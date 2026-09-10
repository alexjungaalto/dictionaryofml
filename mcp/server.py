"""
Dictionary of Applied Machine Learning — MCP server.

Exposes the dictionary (https://dictionaryofml.org) to AI assistants via
the Model Context Protocol: look up a term, search the definitions, walk
the cross-reference graph. The content is fetched from the site's
machine-readable export, https://dictionaryofml.org/terms.json, and cached
on disk for a day, so the server always serves the latest published
edition and works offline once warmed.

Usage:
    pip install -r requirements.txt
    python server.py

Register with Claude Code:
    claude mcp add --scope user dictionaryofml -- python /path/to/server.py
"""

import json
import os
import sys
import time
import urllib.request
from difflib import SequenceMatcher

import asyncio
import mcp.server.stdio
import mcp.types as types
from mcp.server import Server

TERMS_URL = os.environ.get("DICTML_TERMS_URL",
                           "https://dictionaryofml.org/terms.json")
CACHE = os.path.join(os.path.expanduser("~"), ".cache", "dictionaryofml",
                     "terms.json")
CACHE_TTL = 24 * 3600


def load_terms():
    """The terms.json document, from the day-old cache or the site."""
    try:
        if (os.path.exists(CACHE)
                and time.time() - os.path.getmtime(CACHE) < CACHE_TTL):
            return json.load(open(CACHE, encoding="utf-8"))
    except Exception:
        pass
    try:
        with urllib.request.urlopen(TERMS_URL, timeout=30) as r:
            doc = json.loads(r.read().decode("utf-8"))
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        json.dump(doc, open(CACHE, "w", encoding="utf-8"))
        return doc
    except Exception:
        if os.path.exists(CACHE):          # stale cache beats no dictionary
            return json.load(open(CACHE, encoding="utf-8"))
        raise


def by_key(doc):
    return {t["key"]: t for t in doc["terms"]}


def resolve(doc, term):
    """Find a term record by key or (fuzzily) by display name."""
    terms = by_key(doc)
    q = term.strip().lower()
    if q in terms:
        return terms[q]
    for t in doc["terms"]:
        if t["name"].lower() == q:
            return t
    best, score = None, 0.0
    for t in doc["terms"]:
        s = max(SequenceMatcher(None, q, t["name"].lower()).ratio(),
                SequenceMatcher(None, q, t["key"]).ratio())
        if s > score:
            best, score = t, s
    return best if score > 0.6 else None


def fmt(t, full=True):
    lines = [f"# {t['name']}  (key: {t['key']})", ""]
    if t.get("abstract"):
        lines += [t["abstract"], ""]
    if full and t.get("description"):
        lines += ["## Definition", t["description"], ""]
    if t.get("synonyms"):
        lines.append("Synonyms: " + ", ".join(t["synonyms"]))
    if t.get("see_also"):
        lines.append("See also: " + ", ".join(t["see_also"]))
    lines.append(f"Page: {t['url']}  ·  typeset PDF: {t['pdf']}")
    if t.get("demo"):
        lines.append(f"Python demo: {t['demo']}")
    return "\n".join(lines)


server = Server("dictionaryofml")


@server.list_tools()
async def list_tools():
    return [
        types.Tool(
            name="list_all_terms",
            description="List every term of the Dictionary of Applied "
                        "Machine Learning (name and key).",
            inputSchema={"type": "object", "properties": {}}),
        types.Tool(
            name="lookup_term",
            description="Full dictionary entry (abstract, definition, "
                        "cross-references) for a term, by key or name.",
            inputSchema={"type": "object",
                         "properties": {"term": {"type": "string"}},
                         "required": ["term"]}),
        types.Tool(
            name="search_terms",
            description="Search term names and definitions for a keyword "
                        "or phrase; returns the best matches.",
            inputSchema={"type": "object",
                         "properties": {"query": {"type": "string"},
                                        "limit": {"type": "integer"}},
                         "required": ["query"]}),
        types.Tool(
            name="get_related_terms",
            description="The terms a given entry cross-references "
                        "(its See-also list), with their abstracts.",
            inputSchema={"type": "object",
                         "properties": {"term": {"type": "string"}},
                         "required": ["term"]}),
    ]


@server.call_tool()
async def call_tool(name, args):
    doc = load_terms()
    if name == "list_all_terms":
        text = "\n".join(f"- {t['name']}  (key: {t['key']})"
                         for t in doc["terms"])
    elif name == "lookup_term":
        t = resolve(doc, args["term"])
        text = fmt(t) if t else f"No term matching {args['term']!r}."
    elif name == "search_terms":
        q = args["query"].lower()
        limit = int(args.get("limit", 8))
        scored = []
        for t in doc["terms"]:
            hay = " ".join([t["name"], t.get("abstract", ""),
                            t.get("description", "")]).lower()
            s = 3 * (q in t["name"].lower()) + (q in hay) \
                + SequenceMatcher(None, q, t["name"].lower()).ratio()
            if s > 0.4:
                scored.append((s, t))
        scored.sort(key=lambda p: -p[0])
        text = "\n\n".join(fmt(t, full=False) for _, t in scored[:limit]) \
            or f"No matches for {args['query']!r}."
    elif name == "get_related_terms":
        t = resolve(doc, args["term"])
        if not t:
            text = f"No term matching {args['term']!r}."
        else:
            terms = by_key(doc)
            out = []
            for k in t.get("see_also", []):
                r = terms.get(k)
                out.append(f"- {r['name']} (key: {k}): "
                           f"{r.get('abstract', '')[:300]}" if r
                           else f"- {k} (not in the published set)")
            text = f"Terms related to {t['name']}:\n" + "\n".join(out)
    else:
        text = f"Unknown tool {name!r}."
    return [types.TextContent(type="text", text=text)]


async def main():
    async with mcp.server.stdio.stdio_server() as (read, write):
        await server.run(read, write,
                         server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())

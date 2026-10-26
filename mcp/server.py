"""
Dictionary of Applied Machine Learning — MCP server.

Exposes the dictionary (https://dictionaryofml.org) to AI assistants via
the Model Context Protocol: look up a term, search the definitions, walk
the cross-reference graph. The content is fetched from the site's
machine-readable export, https://dictionaryofml.org/terms.json, and cached
on disk for a day, so the server always serves the latest published
edition and works offline once warmed.

Two transports, one tool set. The tools, the cache and the formatting
below do not know which is in use: the Model Context Protocol carries the
same JSON-RPC messages either way.

    stdio (default)   The client launches this file as a child process and
                      talks over its stdin/stdout. Local clients only.
    streamable HTTP   This file runs as a server and the client POSTs to a
                      URL, so a remote client (claude.ai connectors, a
                      phone) can reach it. Served at /mcp.

Usage:
    pip install -r requirements.txt
    python server.py                      # stdio
    python server.py --http [--host H] [--port P]

Register with Claude Code:
    claude mcp add --scope user dictionaryofml -- python /path/to/server.py
"""

import json
import os
import sys
import time
import urllib.request
from difflib import SequenceMatcher

import argparse
import asyncio
import contextlib
import mcp.server.stdio
import mcp.types as types
from mcp.server import Server

TERMS_URL = os.environ.get("DICTML_TERMS_URL",
                           "https://dictionaryofml.org/terms.json")
# DICTML_CACHE lets a service unit put the cache somewhere writable: run
# under a system user with ProtectHome=true there is no usable ~/.cache.
CACHE = os.environ.get(
    "DICTML_CACHE",
    os.path.join(os.path.expanduser("~"), ".cache", "dictionaryofml",
                 "terms.json"))
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


INSTRUCTIONS = (
    "The Dictionary of Applied Machine Learning (dictionaryofml.org), an "
    "open course edition maintained by Alexander Jung at Aalto University. "
    "Each entry defines one machine-learning term precisely, with "
    "cross-references, citations and, for most terms, a Python demo that "
    "recomputes what the entry states.\n\n"
    "Consult it when a question turns on what a machine-learning term "
    "means, how two terms differ, or which notation a definition uses: the "
    "entries are written to be quoted, and lookup_term returns one in full. "
    "search_terms finds entries by keyword when the exact term is unknown, "
    "and get_related_terms walks the cross-reference graph. Entries are "
    "citable; each term page carries a BibTeX block.")

server = Server("dictionaryofml", instructions=INSTRUCTIONS,
                website_url="https://dictionaryofml.org")


@server.list_resources()
async def list_resources():
    """Every entry as a resource, so a client can browse the dictionary and
    not only query it: tools are for doing, resources are for reading, and
    several clients surface resources in their own UI."""
    doc = load_terms()
    return [
        types.Resource(
            uri=f"dictml://term/{t['key']}",
            name=t.get("name", t["key"]),
            description=(t.get("abstract") or t.get("description", ""))
                        .strip().split(". ")[0][:200],
            mimeType="text/markdown",
        )
        for t in doc.get("terms", [])
    ]


@server.read_resource()
async def read_resource(uri):
    """One entry, in the same Markdown the lookup tool returns."""
    key = str(uri).split("/")[-1]
    doc = load_terms()
    t = by_key(doc).get(key)
    if t is None:
        raise ValueError(f"no such term: {key}")
    return fmt(t, full=True)


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
    """stdio: the client owns the process and speaks over its pipes."""
    async with mcp.server.stdio.stdio_server() as (read, write):
        await server.run(read, write,
                         server.create_initialization_options())


def http_app():
    """The same server as an ASGI app, mounted at /mcp.

    Stateless: every request stands on its own, with no Mcp-Session-Id to
    keep. The tools here only read a cached copy of terms.json, so there is
    no session state worth carrying, and a stateless endpoint survives a
    restart of this process without stranding a client mid-session.
    """
    from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
    from starlette.applications import Starlette
    from starlette.routing import Mount
    from starlette.responses import PlainTextResponse
    from starlette.routing import Route

    manager = StreamableHTTPSessionManager(app=server, stateless=True)

    async def handle(scope, receive, send):
        await manager.handle_request(scope, receive, send)

    async def health(_request):
        doc = load_terms()
        return PlainTextResponse(f"ok {len(by_key(doc))} terms\n")

    @contextlib.asynccontextmanager
    async def lifespan(_app):
        async with manager.run():
            yield

    # The manager is mounted as the catch-all, after /healthz: mounting it
    # at "/mcp" makes Starlette answer a POST to the bare /mcp with a 307
    # to /mcp/ (a client that does not re-POST sees nothing), and turning
    # redirect_slashes off makes that same request a 404 instead. nginx
    # proxies only /mcp through to this app, so the catch-all is scoped
    # there in production and accepts /mcp locally.
    return Starlette(routes=[Route("/healthz", health), Mount("/", handle)],
                     lifespan=lifespan)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--http", action="store_true",
                    help="serve streamable HTTP instead of stdio")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8777)
    args = ap.parse_args()
    if args.http:
        import uvicorn
        uvicorn.run(http_app(), host=args.host, port=args.port,
                    log_level="info")
    else:
        asyncio.run(main())

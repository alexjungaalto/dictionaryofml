# Dictionary of Applied ML — MCP server

Exposes [dictionaryofml.org](https://dictionaryofml.org) as a
[Model Context Protocol](https://modelcontextprotocol.io/) server, so AI
assistants can look up, search, and explore the dictionary's terms in
context. Content comes from the site's
[terms.json](https://dictionaryofml.org/terms.json) export, cached locally
for a day — the server always serves the latest published edition.

## Tools

| Tool | Description |
|---|---|
| `list_all_terms` | Every term (name and key) |
| `lookup_term` | Full entry by key or display name (fuzzy) |
| `search_terms` | Keyword search across names and definitions |
| `get_related_terms` | The entry's See-also cross-references, with abstracts |

## Setup

```bash
pip install -r requirements.txt
```

**Claude Code:**

```bash
claude mcp add --scope user dictionaryofml -- python /path/to/mcp/server.py
```

**VS Code (Copilot):** add to your MCP config file
(`~/Library/Application Support/Code/User/mcp.json` on macOS):

```json
{
  "servers": {
    "dictionaryofml": {
      "type": "stdio",
      "command": "python",
      "args": ["/path/to/mcp/server.py"]
    }
  }
}
```

Set `DICTML_TERMS_URL` to point the server at a different terms.json
(e.g. a local build).

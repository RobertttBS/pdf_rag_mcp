---
name: library
description: >
  RAG knowledge base for this project. Search it BEFORE answering questions about
  indexed documents, domain knowledge, or anything the user may have added.
  Use /library add <file> to index a document, /library list to show indexed files,
  /library query <term> to do semantic search and retrieve relevant passages.
argument-hint: add <file> | list | query <term>
allowed-tools:
  - Bash(python3 *)
---

# /library — Local Knowledge Base

Arguments: `$ARGUMENTS`

Run the following command and present the output to the user:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/rag_client.py" "$ARGUMENTS"
```

## Sub-commands

| Command | Description |
|---|---|
| `add <file-path>` | Index a document into the knowledge base |
| `list` | Show all indexed files, chunk counts, and statistics |
| `query <term>` | Semantic search across all indexed documents |

## Important: add then query workflow

After running `add`, indexing happens in the background. Do NOT immediately run
`query` — the new document will not be searchable yet. Instead:

1. Run `add` and confirm the file was accepted.
2. Run `list` and wait until the new filename appears with a non-zero chunk count.
3. Only then run `query`.

## Interpreting query results

Each result shows a `score` (FAISS L2 distance — lower is better). If a
`[WARNING]` line appears saying all scores are above the threshold, the knowledge
base likely does not contain relevant information on the topic; do not treat the
returned passages as authoritative.

## Configuration

Server addresses are resolved in this priority order:

1. **`RAG_SERVER_LIST` env variable** (comma-separated `host:port` list) — overrides everything else.
2. **`rag_config.json`** — edit `skills/library/rag_config.json` to set a persistent IP list.
3. **Fallback** — `localhost:8000`.

When multiple servers are configured, the client tries them in order and automatically
falls back to the next one if a connection cannot be established.
HTTP errors (4xx/5xx) are not retried — they mean the server is reachable but rejected the request.

`rag_config.json` example:
```json
{
  "servers": [
    "192.168.1.100:8000",
    "localhost:8000"
  ]
}
```

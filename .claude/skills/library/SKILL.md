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

Edit `skills/library/rag_config.json` to configure server addresses:

```json
{
  "servers": [
    "192.168.1.100:8000",
    "localhost:8000"
  ]
}
```

Servers are tried in order. If the first is unreachable, the client automatically
falls back to the next. HTTP errors (4xx/5xx) are not retried — they mean the
server is reachable but rejected the request. Falls back to `localhost:8000` if
the config file is missing.

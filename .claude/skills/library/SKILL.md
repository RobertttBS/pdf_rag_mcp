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
  - Read
  - Edit
---

# /library — Local Knowledge Base

Arguments: `$ARGUMENTS`

Run the following command and capture its output and exit code:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/rag_client.py" "$ARGUMENTS"; echo "EXIT_CODE=$?"
```

## Handling connection failures

If the output contains `[ALL_SERVERS_UNREACHABLE]`:

1. Parse `CONFIG_PATH=...` and `CURRENT_SERVERS=...` from the output.
2. Tell the user that none of the configured servers are reachable, and show them the current server list.
3. Ask the user: **"Please provide a reachable server address (format: host:port or IP:port) to add to the config. Leave blank to keep only localhost:8000."**
4. Once the user replies:
   - Read the config file at the path from `CONFIG_PATH=`.
   - Update the `"servers"` list: put the user-supplied address first, keep `"localhost:8000"` as the last fallback (remove any addresses that were already unreachable, unless the user explicitly wants to keep them).
   - Save the updated JSON with the Edit tool.
   - Confirm to the user which servers are now configured.
   - Retry the original command automatically.
5. If the user supplies no address, set `"servers": ["localhost:8000"]` and retry.

Present all other output normally.

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

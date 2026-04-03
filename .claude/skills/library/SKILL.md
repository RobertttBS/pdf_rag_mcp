---
name: library
description: Manage and search the local RAG knowledge base. Use /library add <file> to index a document, /library list to show all indexed files, /library query <term> to do semantic search.
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

## Configuration

Server URL is read from the `RAG_SERVER_LIST` environment variable (default: `localhost:8000`). If multiple servers are listed (comma-separated), the first one is used.

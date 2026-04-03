---
name: query-library
description: Search the local PDF RAG knowledge base using semantic search. Use when the user wants to find information in their indexed documents. Returns the most relevant passages with source file and page number.
argument-hint: <search query>
allowed-tools:
  - Bash(python3 *)
---

# /query-library — Search Knowledge Base

Query: `$ARGUMENTS`

Search the RAG knowledge base for content relevant to the query. The server URL comes from the `RAG_SERVER_LIST` environment variable (default: `localhost:8000`); use the first entry if multiple are listed.

## Steps

1. Run the search:

```bash
python3 - <<'PYEOF'
import json, urllib.request, urllib.error, os, sys

query = """$ARGUMENTS""".strip()
server = os.environ.get("RAG_SERVER_LIST", "localhost:8000").split(",")[0].strip()

if not query:
    print("Error: Please provide a search query.")
    sys.exit(1)

payload = json.dumps({"query": query}).encode()
req = urllib.request.Request(
    f"http://{server}/query",
    data=payload,
    headers={"Content-Type": "application/json"},
)
try:
    resp = urllib.request.urlopen(req, timeout=120)
    data = json.loads(resp.read().decode())
except urllib.error.URLError as e:
    print(f"Error: Cannot reach server at {server} — {e}")
    sys.exit(1)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)

results = data.get("results", [])
if not results:
    print("No relevant results found in the knowledge base.")
else:
    print(f"Search results for '{query}':\n")
    for item in results:
        source = item.get("source", "Unknown")
        page = item.get("page", "N/A")
        content = item.get("content", "")
        print(f"--- {source} (p.{page}) ---")
        print(content)
        print()
PYEOF
```

2. Present the results to the user, synthesizing the content if helpful.

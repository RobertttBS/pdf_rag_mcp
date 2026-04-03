---
name: list-library
description: List all documents indexed in the local PDF RAG knowledge base, including file names, chunk counts, and total statistics. Use when the user asks what's in the knowledge base or library.
allowed-tools:
  - Bash(curl *)
  - Bash(python3 *)
---

# /list-library — List Indexed Documents

Show all documents currently indexed in the RAG knowledge base. The server URL comes from the `RAG_SERVER_LIST` environment variable (default: `localhost:8000`); use the first entry if multiple are listed.

## Steps

1. Fetch and display the document list:

```bash
python3 - <<'PYEOF'
import json, urllib.request, urllib.error, os, sys

server = os.environ.get("RAG_SERVER_LIST", "localhost:8000").split(",")[0].strip()

try:
    resp = urllib.request.urlopen(f"http://{server}/documents", timeout=30)
    data = json.loads(resp.read().decode())
except urllib.error.URLError as e:
    print(f"Error: Cannot reach server at {server} — {e}")
    sys.exit(1)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)

if data.get("total_files", 0) == 0:
    print("Knowledge base is empty. Use /add-document to add files.")
else:
    print(f"Knowledge Base Statistics")
    print("=" * 40)
    print(f"Indexed files : {data['total_files']}")
    print(f"Total chunks  : {data['total_chunks']}")
    print("=" * 40)
    for i, f in enumerate(data["files"], 1):
        page_info = f", {f['pages']} pages" if f.get("pages") else ""
        print(f"{i}. {f['filename']}")
        print(f"   {f['chunks']} chunks{page_info}")
PYEOF
```

2. Present the output clearly to the user.

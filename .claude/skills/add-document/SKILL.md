---
name: add-document
description: Add a document to the local PDF RAG knowledge base for semantic search. Use when the user wants to index a file. Supports PDF, DOCX, PPTX, XLSX, TXT, MD, JSON, YAML, CSV, PY, JS, TS, HTML, CSS, XML, and more.
argument-hint: <file-path>
allowed-tools:
  - Bash(python3 *)
  - Bash(curl *)
---

# /add-document — Add Document to Knowledge Base

File to add: `$ARGUMENTS`

Upload the file to the RAG knowledge base. The server URL comes from the `RAG_SERVER_LIST` environment variable (default: `localhost:8000`); use the first entry if multiple are listed.

## Steps

1. Run the following to upload the file:

```bash
python3 - <<'PYEOF'
import base64, json, urllib.request, urllib.error, os, sys

filepath = """$ARGUMENTS""".strip().strip('"').strip("'")
server = os.environ.get("RAG_SERVER_LIST", "localhost:8000").split(",")[0].strip()

if not os.path.exists(filepath):
    print(f"Error: File not found: {filepath}")
    sys.exit(1)

file_size = os.path.getsize(filepath)
if file_size > 20 * 1024 * 1024:
    print(f"Error: File exceeds 20MB limit ({file_size / 1024 / 1024:.1f}MB)")
    sys.exit(1)

with open(filepath, "rb") as f:
    content = base64.b64encode(f.read()).decode()

filename = os.path.basename(filepath)
payload = json.dumps({"filename": filename, "content_base64": content}).encode()
req = urllib.request.Request(
    f"http://{server}/documents",
    data=payload,
    headers={"Content-Type": "application/json"},
)
try:
    resp = urllib.request.urlopen(req, timeout=120)
    print(resp.read().decode())
except urllib.error.HTTPError as e:
    print(f"Server error {e.code}: {e.read().decode()}")
except Exception as e:
    print(f"Error: {e}")
PYEOF
```

2. Report the result. If successful, inform the user that indexing runs in the background and may take a moment.

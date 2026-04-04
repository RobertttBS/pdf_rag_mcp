#!/usr/bin/env python3
"""
RAG Library Client
Usage:
  rag_client.py add <file-path>   — index a document
  rag_client.py list              — list indexed files and stats
  rag_client.py query <term...>   — semantic search
"""

import base64
import json
import os
import shlex
import sys
import urllib.error
import urllib.request
from typing import Optional

MAX_FILE_SIZE_MB = 20
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# FAISS L2 distance: lower = more similar. Results above this threshold are
# likely irrelevant and should be flagged to the caller.
SCORE_WARN_THRESHOLD = 1.5

# Config file is one level up from this script (i.e. skills/library/rag_config.json)
CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "rag_config.json")

SUPPORTED_EXTENSIONS = {
    ".pdf", ".docx", ".pptx", ".xlsx", ".xls",
    ".md", ".txt", ".log", ".bat", ".sh", ".ps1",
    ".json", ".yaml", ".yml", ".ini", ".cfg", ".conf", ".csv",
    ".py", ".js", ".ts", ".html", ".css", ".xml",
}


def _normalize_host(server: str) -> str:
    """Strip http(s):// prefix so we always prepend http:// ourselves."""
    if server.startswith("http://"):
        return server[len("http://"):]
    if server.startswith("https://"):
        print("Warning: HTTPS is not supported; using HTTP.", file=sys.stderr)
        return server[len("https://"):]
    return server


def get_servers() -> list:
    """
    Return ordered list of server host:port strings from rag_config.json.
    Falls back to ["localhost:8000"] if the config is missing or invalid.
    """
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            servers = [_normalize_host(s.strip()) for s in cfg.get("servers", []) if s.strip()]
            if servers:
                return servers
        except Exception as e:
            print(f"Warning: Could not read {CONFIG_PATH}: {e}", file=sys.stderr)

    return ["localhost:8000"]


def request(method: str, path: str, body: Optional[dict] = None, timeout: int = 120) -> dict:
    servers = get_servers()
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"} if data else {}

    last_error: str = ""
    for i, server in enumerate(servers):
        url = f"http://{server}{path}"
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            resp = urllib.request.urlopen(req, timeout=timeout)
            return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            # HTTP errors (4xx/5xx) mean the server is reachable — don't fall back.
            detail = e.read().decode()
            try:
                detail = json.loads(detail).get("detail", detail)
            except Exception:
                pass
            print(f"Server error {e.code}: {detail}", file=sys.stderr)
            sys.exit(1)
        except urllib.error.URLError as e:
            last_error = str(e.reason)
            if i < len(servers) - 1:
                print(f"Cannot reach {server} ({last_error}), trying next server...", file=sys.stderr)
            else:
                print(f"Cannot reach server at {server}: {last_error}", file=sys.stderr)

    # All servers exhausted — emit a structured signal so the skill can guide the user.
    print(f"[ALL_SERVERS_UNREACHABLE]")
    print(f"CONFIG_PATH={CONFIG_PATH}")
    print(f"CURRENT_SERVERS={','.join(servers)}")
    sys.exit(2)


def cmd_add(file_path: str) -> None:
    file_path = file_path.strip().strip('"').strip("'")

    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        sys.exit(1)

    ext = os.path.splitext(file_path)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        print(f"Error: Unsupported format '{ext}'")
        print(f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}")
        sys.exit(1)

    size = os.path.getsize(file_path)
    if size > MAX_FILE_SIZE_BYTES:
        print(f"Error: File exceeds {MAX_FILE_SIZE_MB}MB limit ({size / 1024 / 1024:.1f}MB)")
        sys.exit(1)

    filename = os.path.basename(file_path)
    with open(file_path, "rb") as f:
        content_b64 = base64.b64encode(f.read()).decode()

    request("POST", "/documents", {"filename": filename, "content_base64": content_b64})
    print(f"[OK] '{filename}' queued for indexing.")
    print("Indexing runs in the background. Wait a moment, then run '/library list' to confirm it appears before querying.")


def cmd_list() -> None:
    data = request("GET", "/documents", timeout=30)

    if data.get("total_files", 0) == 0:
        print("Knowledge base is empty. Use '/library add <file>' to index documents.")
        return

    print("Knowledge Base Statistics")
    print("=" * 40)
    print(f"Indexed files : {data['total_files']}")
    print(f"Total chunks  : {data['total_chunks']}")
    print("=" * 40)
    for i, f in enumerate(data["files"], 1):
        page_info = f", {f['pages']} pages" if f.get("pages") else ""
        print(f"{i}. {f['filename']}")
        print(f"   {f['chunks']} chunks{page_info}")


def cmd_query(query: str) -> None:
    if not query.strip():
        print("Error: Please provide a search query.")
        sys.exit(1)

    data = request("POST", "/query", {"query": query})
    results = data.get("results", [])

    if not results:
        print("No relevant results found in the knowledge base.")
        return

    all_low_relevance = all(r.get("score", 0) > SCORE_WARN_THRESHOLD for r in results)
    if all_low_relevance:
        print(f"[WARNING] All results have low relevance scores (>{SCORE_WARN_THRESHOLD}). "
              "The knowledge base may not contain information on this topic.\n")

    print(f"Search results for '{query}':\n")
    for item in results:
        source = item.get("source", "Unknown")
        page = item.get("page", "N/A")
        content = item.get("content", "")
        score = item.get("score")
        score_str = f"  score={score:.3f}" if score is not None else ""
        print(f"--- {source} (p.{page}){score_str} ---")
        print(content)
        print()


def main() -> None:
    # When invoked from SKILL.md, all arguments arrive as one quoted string (argv[1]).
    # shlex.split() restores proper tokenisation, handling spaces and quoted paths.
    if len(sys.argv) == 2:
        try:
            args = shlex.split(sys.argv[1])
        except ValueError:
            # Unmatched quotes (e.g. apostrophes in natural language). Treat the
            # whole string as a raw query rather than crashing.
            args = sys.argv[1].split()
    else:
        args = sys.argv[1:]

    if not args:
        print(__doc__)
        sys.exit(1)

    action = args[0].lower()

    if action == "add":
        if len(args) < 2:
            print("Usage: library add <file-path>")
            sys.exit(1)
        cmd_add(" ".join(args[1:]))
    elif action == "list":
        cmd_list()
    elif action == "query":
        if len(args) < 2:
            print("Usage: library query <search term>")
            sys.exit(1)
        cmd_query(" ".join(args[1:]))
    else:
        print(f"Unknown action '{action}'. Use: add | list | query")
        sys.exit(1)


if __name__ == "__main__":
    main()

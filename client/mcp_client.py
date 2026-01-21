"""
MCP Client - Thin wrapper for RAG Server

This MCP server exposes the same tools as the original server.py,
but forwards all requests to a remote RAG server via HTTP.

Configuration (environment variables):
- RAG_SERVER_LIST: Comma-separated list of servers (host:port format)
                   Example: "10.8.108.72:9527,192.168.1.100:9527,localhost:8000"
                   Client will try each server in order until one responds.
- RAG_REQUEST_TIMEOUT: Request timeout in seconds (default: 120)
"""

from fastmcp import FastMCP
import os
import sys
import base64
import requests

# Force UTF-8 encoding for Windows (Fixes \U000... garbage text)
if sys.platform == "win32":
    # Reconfigure standard out and error to handle emojis
    if sys.stdout: sys.stdout.reconfigure(encoding='utf-8')
    if sys.stderr: sys.stderr.reconfigure(encoding='utf-8')

# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

RAG_SERVER_LIST_STR = os.environ.get("RAG_SERVER_LIST", "localhost:8000")
RAG_REQUEST_TIMEOUT = int(os.environ.get("RAG_REQUEST_TIMEOUT", "120"))

# Parse server list
SERVER_LIST = []
for server in RAG_SERVER_LIST_STR.split(","):
    server = server.strip()
    if not server:
        continue
    if ":" in server:
        host, port = server.rsplit(":", 1)
        SERVER_LIST.append({"host": host, "port": port, "url": f"http://{host}:{port}"})
    else:
        # Default port 8000 if not specified
        SERVER_LIST.append({"host": server, "port": "8000", "url": f"http://{server}:8000"})

if not SERVER_LIST:
    SERVER_LIST = [{"host": "localhost", "port": "8000", "url": "http://localhost:8000"}]

# Current active server index (sticky: remember last working server)
_current_server_index = 0

# File size limit (must match server)
MAX_FILE_SIZE_MB = 20
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# Supported extensions (for client-side validation)
SUPPORTED_EXTENSIONS = {
    '.pdf', '.docx', '.pptx', '.xlsx', '.xls',
    '.md', '.markdown',
    '.txt', '.log',
    '.bat', '.sh', '.ps1',
    '.json', '.yaml', '.yml', '.ini', '.cfg', '.conf',
    '.csv',
    '.py', '.js', '.ts', '.html', '.css', '.xml'
}

# ---------------------------------------------------------
# MCP Server
# ---------------------------------------------------------

mcp = FastMCP("My Local Library", log_level="info")

# ---------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------

def get_file_extension(file_path: str) -> str:
    """Get file extension (lowercase)."""
    return os.path.splitext(file_path)[1].lower()

def make_request(method: str, endpoint: str, **kwargs) -> dict:
    """
    Make HTTP request to RAG server with failover support.
    
    Tries each server in SERVER_LIST in order, starting from the last
    successful server (sticky). If a server fails with ConnectionError,
    automatically tries the next server.
    
    Returns:
        dict with 'success' (bool) and either 'data' or 'error'
    """
    global _current_server_index
    
    connection_errors = []
    num_servers = len(SERVER_LIST)
    
    # Try each server, starting from current index
    for attempt in range(num_servers):
        idx = (_current_server_index + attempt) % num_servers
        server = SERVER_LIST[idx]
        url = f"{server['url']}{endpoint}"
        
        try:
            if method == "GET":
                response = requests.get(url, timeout=RAG_REQUEST_TIMEOUT, **kwargs)
            elif method == "POST":
                response = requests.post(url, timeout=RAG_REQUEST_TIMEOUT, **kwargs)
            else:
                return {"success": False, "error": f"Unsupported method: {method}"}
            
            # Check for HTTP errors
            if response.status_code >= 400:
                try:
                    error_detail = response.json().get("detail", response.text)
                except Exception:
                    error_detail = response.text
                return {
                    "success": False,
                    "error": f"Server error ({response.status_code}): {error_detail}"
                }
            
            # Success! Update sticky server index
            if idx != _current_server_index:
                print(f"[Failover] Switched to server: {server['host']}:{server['port']}", file=sys.stderr)
                _current_server_index = idx
            
            return {"success": True, "data": response.json()}
        
        except requests.exceptions.ConnectionError:
            connection_errors.append(f"{server['host']}:{server['port']}")
            # Try next server
            continue
        
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": f"Error: Server {server['host']}:{server['port']} timed out after {RAG_REQUEST_TIMEOUT}s"
            }
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"Error: Request to {server['host']}:{server['port']} failed - {str(e)}"
            }
    
    # All servers failed with connection errors
    return {
        "success": False,
        "error": f"Error: All servers unreachable. Tried: {', '.join(connection_errors)}"
    }

# ---------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------

@mcp.tool()
def add_document_to_library(file_path: str) -> str:
    """[Single file] Add document to knowledge base
    
    Supported formats: PDF, DOCX, PPTX, XLSX, XLS, MD, TXT, LOG, BAT, SH, PS1, JSON, YAML, YML, INI, CFG, CONF, CSV, PY, JS, TS, HTML, CSS, XML
    """
    # Clean up path
    file_path = file_path.strip('"').strip("'")
    
    # Check if file exists
    if not os.path.exists(file_path):
        return f"Error: File not found -> {file_path}"
    
    # Check file extension
    ext = get_file_extension(file_path)
    if ext not in SUPPORTED_EXTENSIONS:
        return f"Error: Unsupported format '{ext}'\nSupported formats: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
    
    # Check file size
    file_size = os.path.getsize(file_path)
    if file_size > MAX_FILE_SIZE_BYTES:
        return f"Error: File exceeds {MAX_FILE_SIZE_MB}MB limit (got {file_size / 1024 / 1024:.1f}MB)"
    
    # Read and encode file
    try:
        with open(file_path, 'rb') as f:
            file_content = f.read()
        content_base64 = base64.b64encode(file_content).decode('utf-8')
    except Exception as e:
        return f"Error: Failed to read file - {str(e)}"
    
    # Send to server
    filename = os.path.basename(file_path)
    result = make_request(
        "POST",
        "/documents",
        json={"filename": filename, "content_base64": content_base64}
    )
    
    if result["success"]:
        data = result["data"]
        return f"[OK] Added '{filename}' with {data.get('chunks_added', '?')} chunks to knowledge base. Server is indexing, please wait..."
    else:
        return result["error"]

@mcp.tool()
def list_indexed_files() -> str:
    """[Query] List all indexed documents and statistics in knowledge base"""
    result = make_request("GET", "/documents")
    
    if not result["success"]:
        return result["error"]
    
    data = result["data"]
    
    if data["total_files"] == 0:
        return "[EMPTY] Knowledge base is empty. Use add_document_to_library to add documents."
    
    response = f"Knowledge Base Statistics\n"
    response += f"{'='*40}\n"
    response += f"Indexed files: {data['total_files']}\n"
    response += f"Total chunks: {data['total_chunks']}\n"
    response += f"{'='*40}\n\n"
    response += f"Indexed files list:\n"
    response += f"{'-'*40}\n"
    
    for idx, file_info in enumerate(data["files"], 1):
        page_info = f", {file_info['pages']} pages" if file_info.get('pages') else ""
        response += f"{idx}. {file_info['filename']}\n"
        response += f"   - {file_info['chunks']} chunks{page_info}\n"
    
    return response

@mcp.tool()
def query_library(query: str) -> str:
    """[Search] Search for relevant information in knowledge base"""
    result = make_request("POST", "/query", json={"query": query})
    
    if not result["success"]:
        # Check if it's a "knowledge base empty" error
        if "empty" in result["error"].lower():
            return "Knowledge base is empty. Please add documents first."
        return result["error"]
    
    data = result["data"]
    
    if not data["results"]:
        return "No relevant information found in knowledge base."
    
    response = f"Search results for '{query}':\n\n"
    for item in data["results"]:
        source = item.get("source", "Unknown")
        page = item.get("page", "N/A")
        content = item.get("content", "")
        response += f"--- {source} (P.{page}) ---\n{content}\n\n"
    
    return response

# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

def find_available_server() -> bool:
    """
    Try to find an available server from SERVER_LIST.
    Updates _current_server_index to point to the first working server.
    
    Returns:
        True if a working server is found, False otherwise.
    """
    global _current_server_index
    
    for idx, server in enumerate(SERVER_LIST):
        url = f"{server['url']}/health"
        try:
            response = requests.get(url, timeout=5)  # Short timeout for health check
            if response.status_code == 200:
                _current_server_index = idx
                return True
        except requests.exceptions.RequestException:
            continue
    return False


if __name__ == "__main__":
    import traceback
    
    log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug_error.log")
    
    try:
        print(f"[System] Starting MCP Client...", file=sys.stderr)
        print(f"[System] Server list ({len(SERVER_LIST)} servers):", file=sys.stderr)
        for i, server in enumerate(SERVER_LIST):
            print(f"  [{i+1}] {server['host']}:{server['port']}", file=sys.stderr)
        
        # Check server health - try to find any available server
        print("[System] Checking server connections...", file=sys.stderr)
        if find_available_server():
            active = SERVER_LIST[_current_server_index]
            print(f"[OK] Connected to: {active['host']}:{active['port']}", file=sys.stderr)
        else:
            print("[WARNING] No servers available", file=sys.stderr)
            print("[WARNING] MCP will start, but requests may fail until a server is available", file=sys.stderr)
        
        print("[System] MCP Server ready.", file=sys.stderr)
        mcp.run()
    
    except Exception:
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(traceback.format_exc())
        sys.exit(1)

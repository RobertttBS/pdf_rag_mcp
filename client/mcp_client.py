"""
MCP Client - Thin wrapper for RAG Server

This MCP server exposes the same tools as the original server.py,
but forwards all requests to a remote RAG server via HTTP.

Configuration (environment variables):
- RAG_SERVER_HOST: Server hostname (default: localhost)
- RAG_SERVER_PORT: Server port (default: 8000)
- RAG_REQUEST_TIMEOUT: Request timeout in seconds (default: 120)
"""

from fastmcp import FastMCP
import os
import sys
import base64
import requests

# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

RAG_SERVER_HOST = os.environ.get("RAG_SERVER_HOST", "localhost")
RAG_SERVER_PORT = os.environ.get("RAG_SERVER_PORT", "8000")
RAG_REQUEST_TIMEOUT = int(os.environ.get("RAG_REQUEST_TIMEOUT", "120"))

BASE_URL = f"http://{RAG_SERVER_HOST}:{RAG_SERVER_PORT}"

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

mcp = FastMCP("My Local Library")

# ---------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------

def get_file_extension(file_path: str) -> str:
    """Get file extension (lowercase)."""
    return os.path.splitext(file_path)[1].lower()

def make_request(method: str, endpoint: str, **kwargs) -> dict:
    """
    Make HTTP request to RAG server with error handling.
    
    Returns:
        dict with 'success' (bool) and either 'data' or 'error'
    """
    url = f"{BASE_URL}{endpoint}"
    
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
        
        return {"success": True, "data": response.json()}
    
    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "error": f"Error: Cannot connect to RAG server at {RAG_SERVER_HOST}:{RAG_SERVER_PORT}. Is the server running?"
        }
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": f"Error: Server request timed out after {RAG_REQUEST_TIMEOUT} seconds"
        }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"Error: Request failed - {str(e)}"
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
        return f"[OK] Added '{filename}' with {data.get('chunks_added', '?')} chunks to knowledge base."
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

if __name__ == "__main__":
    import traceback
    
    log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug_error.log")
    
    try:
        print(f"[System] Starting MCP Client...", file=sys.stderr)
        print(f"[System] RAG Server: {BASE_URL}", file=sys.stderr)
        
        # Check server health
        print("[System] Checking server connection...", file=sys.stderr)
        result = make_request("GET", "/health")
        if result["success"]:
            print("[OK] Server connection successful", file=sys.stderr)
        else:
            print(f"[WARNING] {result['error']}", file=sys.stderr)
            print("[WARNING] MCP will start, but requests may fail until server is available", file=sys.stderr)
        
        print("[System] MCP Server ready.", file=sys.stderr)
        mcp.run()
    
    except Exception:
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(traceback.format_exc())
        sys.exit(1)

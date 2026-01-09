from fastmcp import FastMCP
import os
import sys
import warnings
import traceback

# ---------------------------------------------------------
# Set model cache directory to ./models/ (relative to script location)
# This ensures HuggingFace & Sentence Transformers models download locally
# ---------------------------------------------------------

def get_base_path():
    """
    Determine execution environment:
    - If packaged exe, use executable folder (sys.executable)
    - If python script, use script folder (__file__)
    """
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = get_base_path()
MODELS_DIR = os.path.join(BASE_DIR, "models")
DB_DIR = os.path.join(BASE_DIR, "faiss_index")

# Create models directory if not exists
os.makedirs(MODELS_DIR, exist_ok=True)

# Set environment variables for model cache BEFORE importing transformers/sentence-transformers
os.environ["HF_HOME"] = MODELS_DIR
os.environ["TRANSFORMERS_CACHE"] = MODELS_DIR
os.environ["SENTENCE_TRANSFORMERS_HOME"] = MODELS_DIR

# Suppress warnings
warnings.filterwarnings("ignore")

mcp = FastMCP("My Local Library")

# ---------------------------------------------------------
# Lazy loading with Singleton pattern for embedding model
# ---------------------------------------------------------
_embedding_function = None

def get_embedding_function():
    """
    Lazy load embedding model.
    Only imports and downloads model on first tool call.
    """
    global _embedding_function
    if _embedding_function is None:
        from langchain_huggingface import HuggingFaceEmbeddings
        
        print("[INFO] Loading AI model (first run may be slow)...", file=sys.stderr)
        _embedding_function = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        print("[OK] Model loaded successfully", file=sys.stderr)
    return _embedding_function

def get_db():
    """Get DB instance with lazy FAISS loading"""
    from langchain_community.vectorstores import FAISS
    
    embedding_func = get_embedding_function()
    
    if os.path.exists(DB_DIR) and os.path.exists(os.path.join(DB_DIR, "index.faiss")):
        return FAISS.load_local(DB_DIR, embedding_func, allow_dangerous_deserialization=True)
    return None

def save_db(db):
    """Save index to disk"""
    db.save_local(DB_DIR)

# Supported file extensions
SUPPORTED_EXTENSIONS = {
    # Documents
    '.pdf', '.docx', '.pptx', '.xlsx', '.xls',
    # Markdown
    '.md', '.markdown',
    # Plain text
    '.txt', '.log',
    # Scripts
    '.bat', '.sh', '.ps1',
    # Config files
    '.json', '.yaml', '.yml', '.ini', '.cfg', '.conf',
    # Data files
    '.csv',
    # Code
    '.py', '.js', '.ts', '.html', '.css', '.xml'
}

# Plain text extensions for unified handling
TEXT_EXTENSIONS = {
    '.txt', '.log',
    '.bat', '.sh', '.ps1',
    '.json', '.yaml', '.yml', '.ini', '.cfg', '.conf',
    '.csv',
    '.py', '.js', '.ts', '.html', '.css', '.xml'
}

# Batch processing settings
BATCH_SIZE = 10

def get_indexed_sources(db) -> set:
    """
    Get set of indexed file names for duplicate detection.
    
    Returns:
        set: Set of indexed source file names
    """
    if not db or not hasattr(db, 'docstore') or not hasattr(db.docstore, '_dict'):
        return set()
    return {doc.metadata.get('source') for doc in db.docstore._dict.values() if doc.metadata.get('source')}

def get_file_extension(file_path: str) -> str:
    """Get file extension (lowercase)"""
    return os.path.splitext(file_path)[1].lower()

def load_document(file_path: str):
    """
    Universal document loader: auto-selects appropriate loader based on file type
    
    Supported formats:
    - PDF (.pdf)
    - Word (.docx)
    - PowerPoint (.pptx)
    - Excel (.xlsx, .xls)
    - Markdown (.md, .markdown)
    - Plain text (.txt, .log)
    - Scripts (.bat, .sh, .ps1)
    - Config files (.json, .yaml, .yml, .ini, .cfg, .conf)
    - Data files (.csv)
    - Code (.py, .js, .ts, .html, .css, .xml)
    
    Returns:
        list: List of Document objects
    """
    from langchain_core.documents import Document
    
    ext = get_file_extension(file_path)
    file_name = os.path.basename(file_path)
    
    try:
        if ext == '.pdf':
            try:
                import pypdf
            except ImportError:
                print("[ERROR] Missing pypdf module, run: pip install pypdf", file=sys.stderr)
                return []
            from langchain_community.document_loaders import PyPDFLoader
            loader = PyPDFLoader(file_path)
            return loader.load()
        
        elif ext == '.docx':
            import docx2txt
            text = docx2txt.process(file_path)
            if text.strip():
                return [Document(
                    page_content=text,
                    metadata={"source": file_name, "file_type": "docx"}
                )]
            return []
        
        elif ext == '.pptx':
            from pptx import Presentation
            prs = Presentation(file_path)
            documents = []
            for slide_num, slide in enumerate(prs.slides, 1):
                slide_text = []
                for shape in slide.shapes:
                    if hasattr(shape, "text") and shape.text.strip():
                        slide_text.append(shape.text)
                if slide_text:
                    documents.append(Document(
                        page_content="\n".join(slide_text),
                        metadata={"source": file_name, "page": slide_num, "file_type": "pptx"}
                    ))
            return documents
        
        elif ext in ['.xlsx', '.xls']:
            import openpyxl
            wb = openpyxl.load_workbook(file_path, data_only=True)
            documents = []
            for sheet_name in wb.sheetnames:
                sheet = wb[sheet_name]
                rows_text = []
                for row in sheet.iter_rows(max_row=1000):
                    row_values = [str(cell.value) if cell.value is not None else "" for cell in row]
                    if any(v.strip() for v in row_values):
                        rows_text.append(" | ".join(row_values))
                if rows_text:
                    documents.append(Document(
                        page_content="\n".join(rows_text),
                        metadata={"source": file_name, "sheet": sheet_name, "file_type": "excel"}
                    ))
            return documents
        
        elif ext in ['.md', '.markdown']:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            if text.strip():
                return [Document(
                    page_content=text,
                    metadata={"source": file_name, "file_type": "markdown"}
                )]
            return []
        
        elif ext in TEXT_EXTENSIONS:
            import chardet
            
            try:
                with open(file_path, 'rb') as f:
                    raw_data = f.read()
                
                detected = chardet.detect(raw_data)
                encoding = detected.get('encoding', 'utf-8') or 'utf-8'
                confidence = detected.get('confidence', 0)
                
                text = raw_data.decode(encoding, errors='ignore')
                
                if text.strip():
                    file_type_map = {
                        '.txt': 'text', '.log': 'log',
                        '.bat': 'script', '.sh': 'script', '.ps1': 'script',
                        '.json': 'config', '.yaml': 'config', '.yml': 'config',
                        '.ini': 'config', '.cfg': 'config', '.conf': 'config',
                        '.csv': 'data',
                        '.py': 'code', '.js': 'code', '.ts': 'code',
                        '.html': 'code', '.css': 'code', '.xml': 'code'
                    }
                    file_type = file_type_map.get(ext, 'text')
                    
                    return [Document(
                        page_content=text,
                        metadata={
                            "source": file_name,
                            "file_type": file_type,
                            "encoding": encoding,
                            "encoding_confidence": round(confidence, 2)
                        }
                    )]
            except Exception as e:
                print(f"[ERROR] Reading text file {file_path}: {e}", file=sys.stderr)
            return []
        
        else:
            return []
    
    except Exception as e:
        print(f"[ERROR] Loading document {file_path}: {e}", file=sys.stderr)
        return []


@mcp.tool()
def add_folder_to_library(folder_path: str):
    """[Batch] Read all supported documents in a folder and add to knowledge base
    
    Supported formats: PDF, DOCX, PPTX, XLSX, XLS, MD, TXT, LOG, BAT, SH, PS1, JSON, YAML, YML, INI, CFG, CONF, CSV, PY, JS, TS, HTML, CSS, XML
    
    Features:
    - Batch FAISS writes (every N files, reduces memory usage)
    - Auto-skip indexed files (duplicate detection)
    - Progress reporting (stderr output)
    - Fault-tolerant (partial saves on interruption)
    """
    import glob
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_community.vectorstores import FAISS

    folder_path = folder_path.strip('"').strip("'")
    
    if not os.path.exists(folder_path):
        return f"Error: Folder not found -> {folder_path}"

    all_files = []
    for ext in SUPPORTED_EXTENSIONS:
        all_files.extend(glob.glob(os.path.join(folder_path, f"*{ext}")))
        all_files.extend(glob.glob(os.path.join(folder_path, f"*{ext.upper()}")))
    
    all_files = sorted(set(all_files))
    
    if not all_files:
        supported_list = ", ".join(SUPPORTED_EXTENSIONS)
        return f"No supported files found in '{folder_path}'.\nSupported formats: {supported_list}"

    current_db = get_db()
    indexed_sources = get_indexed_sources(current_db)
    
    files_to_process = []
    skipped_files = []
    for file_path in all_files:
        file_name = os.path.basename(file_path)
        if file_name in indexed_sources:
            skipped_files.append(file_name)
        else:
            files_to_process.append(file_path)
    
    if not files_to_process:
        if skipped_files:
            return f"All {len(skipped_files)} files in folder are already indexed, no action needed."
        return "No files to process."

    total_files = len(files_to_process)
    print(f"[START] Processing {total_files} new files, skipped {len(skipped_files)} duplicates", file=sys.stderr)
    
    processed_files = []
    failed_files = []
    total_splits_count = 0
    batch_count = 0
    
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=100)
    embedding_func = get_embedding_function()
    
    batch_splits = []

    for idx, file_path in enumerate(files_to_process, 1):
        file_name = os.path.basename(file_path)
        
        print(f"[{idx}/{total_files}] Processing: {file_name}", file=sys.stderr)
        
        try:
            docs = load_document(file_path)
            if docs:
                splits = text_splitter.split_documents(docs)
                if splits:
                    for split in splits:
                        split.metadata["source"] = file_name
                    batch_splits.extend(splits)
                    processed_files.append(file_name)
                else:
                    failed_files.append((file_name, "Empty content"))
            else:
                failed_files.append((file_name, "Failed to read content"))
        except Exception as e:
            failed_files.append((file_name, str(e)))
            print(f"[ERROR] {file_name}: {e}", file=sys.stderr)
        
        if len(processed_files) > 0 and (len(processed_files) % BATCH_SIZE == 0 or idx == total_files):
            if batch_splits:
                try:
                    batch_count += 1
                    print(f"[BATCH {batch_count}] Writing {len(batch_splits)} chunks to FAISS...", file=sys.stderr)
                    
                    current_db = get_db()
                    
                    if current_db:
                        current_db.add_documents(batch_splits)
                        save_db(current_db)
                    else:
                        new_db = FAISS.from_documents(batch_splits, embedding_func)
                        save_db(new_db)
                    
                    total_splits_count += len(batch_splits)
                    batch_splits = []
                    print(f"[BATCH {batch_count}] Done! Total chunks written: {total_splits_count}", file=sys.stderr)
                    
                except Exception as e:
                    error_msg = f"Error writing batch {batch_count}: {str(e)}"
                    print(f"[CRITICAL] {error_msg}", file=sys.stderr)
                    return f"[WARNING] Partial processing completed, error at batch {batch_count}.\n" \
                           f"Files processed: {len(processed_files) - len(batch_splits)}\n" \
                           f"Chunks written: {total_splits_count}\n" \
                           f"Error: {error_msg}"

    result = f"[OK] Batch processing complete!\n"
    result += f"{'='*40}\n"
    result += f"Files processed: {len(processed_files)}\n"
    result += f"Chunks added: {total_splits_count}\n"
    result += f"Batches written: {batch_count}\n"
    
    if skipped_files:
        result += f"\nSkipped {len(skipped_files)} duplicate files (already in knowledge base)\n"
    
    if failed_files:
        result += f"\n[WARNING] {len(failed_files)} files failed:\n"
        for file_name, reason in failed_files:
            result += f"  - {file_name}: {reason}\n"
    
    return result


@mcp.tool()
def add_pdf_to_library(pdf_path: str):
    """[Single file] Add PDF to knowledge base (legacy, use add_document_to_library)"""
    return add_document_to_library(pdf_path)


@mcp.tool()
def add_document_to_library(file_path: str):
    """[Single file] Add document to knowledge base
    
    Supported formats: PDF, DOCX, PPTX, XLSX, XLS, MD, TXT, LOG, BAT, SH, PS1, JSON, YAML, YML, INI, CFG, CONF, CSV, PY, JS, TS, HTML, CSS, XML
    """
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_community.vectorstores import FAISS

    file_path = file_path.strip('"').strip("'")
    
    if not os.path.exists(file_path):
        return f"Error: File not found -> {file_path}"
    
    ext = get_file_extension(file_path)
    if ext not in SUPPORTED_EXTENSIONS:
        supported_list = ", ".join(SUPPORTED_EXTENSIONS)
        return f"Error: Unsupported format '{ext}'\nSupported formats: {supported_list}"

    try:
        docs = load_document(file_path)
        
        if not docs:
            return f"Empty or unreadable document: {os.path.basename(file_path)}"
        
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=100)
        splits = text_splitter.split_documents(docs)
        
        if not splits:
            return "Document content is empty or unreadable."

        for split in splits:
            split.metadata["source"] = os.path.basename(file_path)

        current_db = get_db()
        embedding_func = get_embedding_function()

        if current_db:
            current_db.add_documents(splits)
            save_db(current_db)
        else:
            new_db = FAISS.from_documents(splits, embedding_func)
            save_db(new_db)
        
        return f"[OK] Added '{os.path.basename(file_path)}' with {len(splits)} chunks to knowledge base."
    
    except Exception as e:
        return f"Error processing document: {str(e)}"


@mcp.tool()
def list_indexed_files():
    """[Query] List all indexed documents and statistics in knowledge base"""
    try:
        db = get_db()
        if not db:
            return "[EMPTY] Knowledge base is empty. Use add_pdf_to_library or add_folder_to_library to add documents."

        sources_info = {}
        total_chunks = 0
        
        for doc_id in db.docstore._dict:
            doc = db.docstore._dict[doc_id]
            source = doc.metadata.get('source', 'Unknown')
            page = doc.metadata.get('page', None)
            
            if source not in sources_info:
                sources_info[source] = {'pages': set(), 'chunks': 0}
            
            sources_info[source]['chunks'] += 1
            if page is not None:
                sources_info[source]['pages'].add(page)
            total_chunks += 1

        file_count = len(sources_info)
        result = f"Knowledge Base Statistics\n"
        result += f"{'='*40}\n"
        result += f"Indexed files: {file_count}\n"
        result += f"Total chunks: {total_chunks}\n"
        result += f"{'='*40}\n\n"
        result += f"Indexed files list:\n"
        result += f"{'-'*40}\n"
        
        for idx, (source, info) in enumerate(sorted(sources_info.items()), 1):
            page_info = f", {len(info['pages'])} pages" if info['pages'] else ""
            result += f"{idx}. {source}\n"
            result += f"   - {info['chunks']} chunks{page_info}\n"
        
        return result

    except Exception as e:
        return f"Error querying index: {str(e)}"


@mcp.tool()
def query_library(query: str):
    """[Search] Search for relevant information in knowledge base"""
    try:
        db = get_db()
        if not db:
            return "Knowledge base is empty. Please add documents first."

        results = db.similarity_search(query, k=4)
        
        if not results:
            return "No relevant information found in knowledge base."

        response_text = f"Search results for '{query}':\n\n"
        for doc in results:
            source = doc.metadata.get('source', 'Unknown')
            page = doc.metadata.get('page', 'N/A')
            response_text += f"--- {source} (P.{page}) ---\n{doc.page_content}\n\n"
            
        return response_text
        
    except Exception as e:
        return f"Error during search: {str(e)}"


if __name__ == "__main__":
    log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug_error.log")
    try:
        mcp.run()
    except Exception:
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(traceback.format_exc())
        sys.exit(1)

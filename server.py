from fastmcp import FastMCP
import os
import sys
import warnings
import traceback

# ---------------------------------------------------------
# 修改點 1: 移除頂層的 Heavy Imports
# 只保留 os, sys, fastmcp 等輕量級套件
# 這樣 Server 啟動時就不會卡在載入 PyTorch/LangChain
# ---------------------------------------------------------

# 忽略警告
warnings.filterwarnings("ignore")

mcp = FastMCP("My Local Library")

def get_base_path():
    """
    判斷執行環境：
    如果是打包後的 exe，使用執行檔所在的資料夾 (sys.executable)
    如果是原始 python script，使用檔案所在的資料夾 (__file__)
    """
    if getattr(sys, 'frozen', False):
        # 如果是打包後的 exe
        return os.path.dirname(sys.executable)
    else:
        # 如果是開發中的 .py
        return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = get_base_path()
DB_DIR = os.path.join(BASE_DIR, "faiss_index")

# ---------------------------------------------------------
# 修改點 2: 使用全域變數配合 Singleton 模式延遲載入
# ---------------------------------------------------------
_embedding_function = None

def get_embedding_function():
    """
    延遲載入 Embedding 模型。
    只有在第一次呼叫工具時才會執行 import 和模型下載。
    """
    global _embedding_function
    if _embedding_function is None:
        # 將 import 移到這裡，避免啟動時卡住
        from langchain_huggingface import HuggingFaceEmbeddings
        
        print("正在載入 AI 模型 (第一次執行會較慢)...", file=sys.stderr)
        _embedding_function = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    return _embedding_function

def get_db():
    """統一取得 DB 實例 (包含延遲載入 FAISS)"""
    # 將 import 移到這裡
    from langchain_community.vectorstores import FAISS
    
    # 確保模型已載入
    embedding_func = get_embedding_function()
    
    if os.path.exists(DB_DIR) and os.path.exists(os.path.join(DB_DIR, "index.faiss")):
        return FAISS.load_local(DB_DIR, embedding_func, allow_dangerous_deserialization=True)
    return None

def save_db(db):
    """將索引存回硬碟"""
    db.save_local(DB_DIR)

# ---------------------------------------------------------
# 修改點 3: 將工具所需的 Import 移至函式內部
# ---------------------------------------------------------

@mcp.tool()
def add_folder_to_library(folder_path: str):
    """[批次處理] 讀取資料夾內 PDF 並加入知識庫"""
    # Import moved locally
    import glob
    from langchain_community.document_loaders import PyPDFLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_community.vectorstores import FAISS

    folder_path = folder_path.strip('"').strip("'")
    
    if not os.path.exists(folder_path):
        return f"錯誤：找不到資料夾 -> {folder_path}"

    pdf_files = glob.glob(os.path.join(folder_path, "*.pdf"))
    if not pdf_files:
        return f"在 '{folder_path}' 中找不到任何 PDF 檔案。"

    all_splits = []
    processed_files = []
    
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=100)

    # 1. 讀取並切分
    for pdf_file in pdf_files:
        try:
            loader = PyPDFLoader(pdf_file)
            docs = loader.load()
            splits = text_splitter.split_documents(docs)
            if splits:
                for split in splits:
                    split.metadata["source"] = os.path.basename(pdf_file)
                all_splits.extend(splits)
                processed_files.append(os.path.basename(pdf_file))
        except Exception as e:
            print(f"Error reading {pdf_file}: {e}", file=sys.stderr)

    if not all_splits:
        return "沒有成功讀取到任何內容。"

    # 2. 寫入 FAISS
    try:
        current_db = get_db()
        embedding_func = get_embedding_function() # 確保取得模型
        
        if current_db:
            current_db.add_documents(all_splits)
            save_db(current_db)
        else:
            # 需要用到 FAISS class，所以上面有 import
            new_db = FAISS.from_documents(all_splits, embedding_func)
            save_db(new_db)
        
        return f"批次處理完成！共處理 {len(processed_files)} 個檔案，新增 {len(all_splits)} 個片段。"
    except Exception as e:
        return f"寫入資料庫時發生錯誤: {str(e)}"

@mcp.tool()
def add_pdf_to_library(pdf_path: str):
    """[單檔處理] 將 PDF 加入知識庫"""
    # Import moved locally
    from langchain_community.document_loaders import PyPDFLoader
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_community.vectorstores import FAISS

    pdf_path = pdf_path.strip('"').strip("'")
    
    if not os.path.exists(pdf_path):
        return f"錯誤：找不到檔案 -> {pdf_path}"

    try:
        loader = PyPDFLoader(pdf_path)
        docs = loader.load()
        
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=100)
        splits = text_splitter.split_documents(docs)
        
        if not splits:
            return "PDF 內容為空或無法讀取。"

        # 寫入 FAISS
        current_db = get_db()
        embedding_func = get_embedding_function()

        if current_db:
            current_db.add_documents(splits)
            save_db(current_db)
        else:
            new_db = FAISS.from_documents(splits, embedding_func)
            save_db(new_db)
        
        return f"成功！已將 '{os.path.basename(pdf_path)}' 的 {len(splits)} 個片段加入知識庫。"
    
    except Exception as e:
        return f"處理 PDF 時發生錯誤: {str(e)}"

@mcp.tool()
def list_indexed_files():
    """[查詢] 列出知識庫中已索引的所有文件及統計資訊"""
    try:
        db = get_db()
        if not db:
            return "📭 知識庫目前是空的，請先使用 add_pdf_to_library 或 add_folder_to_library 加入文件。"

        # 從 docstore 中提取所有文件的 metadata
        sources_info = {}  # source -> {'pages': set(), 'chunks': count}
        total_chunks = 0
        
        for doc_id in db.docstore._dict:
            doc = db.docstore._dict[doc_id]
            source = doc.metadata.get('source', '未知來源')
            page = doc.metadata.get('page', None)
            
            if source not in sources_info:
                sources_info[source] = {'pages': set(), 'chunks': 0}
            
            sources_info[source]['chunks'] += 1
            if page is not None:
                sources_info[source]['pages'].add(page)
            total_chunks += 1

        # 組合輸出結果
        file_count = len(sources_info)
        result = f"📚 知識庫統計資訊\n"
        result += f"{'='*40}\n"
        result += f"📁 已索引文件數量: {file_count}\n"
        result += f"📄 總片段數量: {total_chunks}\n"
        result += f"{'='*40}\n\n"
        result += f"📋 已索引文件清單:\n"
        result += f"{'-'*40}\n"
        
        for idx, (source, info) in enumerate(sorted(sources_info.items()), 1):
            page_info = f", 共 {len(info['pages'])} 頁" if info['pages'] else ""
            result += f"{idx}. {source}\n"
            result += f"   └─ {info['chunks']} 個片段{page_info}\n"
        
        return result

    except Exception as e:
        return f"查詢索引時發生錯誤: {str(e)}"

@mcp.tool()
def query_library(query: str):
    """[搜尋] 從知識庫搜尋相關資訊"""
    try:
        # get_db 內部會處理 FAISS 的 import
        db = get_db()
        if not db:
            return "知識庫目前是空的，請先加入 PDF 檔案。"

        results = db.similarity_search(query, k=4)
        
        if not results:
            return "在知識庫中找不到相關資訊。"

        response_text = f"針對 '{query}' 的搜尋結果:\n\n"
        for doc in results:
            source = doc.metadata.get('source', '未知來源')
            page = doc.metadata.get('page', 'N/A')
            response_text += f"--- {source} (P.{page}) ---\n{doc.page_content}\n\n"
            
        return response_text
        
    except Exception as e:
        return f"搜尋時發生錯誤: {str(e)}"

if __name__ == "__main__":
    log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug_error.log")
    try:
        mcp.run()
    except Exception:
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(traceback.format_exc())
        sys.exit(1)
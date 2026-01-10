# 📚 Local Library MCP - 本地知識庫搜尋工具

這是一個 **Cursor MCP (Model Context Protocol)** 伺服器，可以讓 Cursor AI 助手直接搜尋你的本地文件知識庫。

> **原理簡介**：將 PDF、Word、Excel、PowerPoint 等文件轉換成向量索引，讓 AI 能夠語意搜尋相關內容。

---

## 🏗️ 架構說明

本專案採用 **Client-Server 架構**：

```
┌─────────────────┐         HTTP          ┌─────────────────┐
│  Cursor + MCP   │ ──────────────────▶  │   RAG Server    │
│  Client (輕量)   │ ◀──────────────────   │  (FastAPI)      │
└─────────────────┘                       └─────────────────┘
                                                  │
                                                  ▼
                                          ┌──────────────┐
                                          │ FAISS Index  │
                                          │ + AI Model   │
                                          └──────────────┘
```

**優點**：

- 🖥️ Server 可部署在高效能機器上 (AI Embedding 需要較強 CPU)
- 👥 多個 Client 可共享同一個知識庫
- 🚀 Client 端輕量，不需下載 AI 模型

---

## 🚀 快速開始

### 步驟 1：啟動 Server (在高效能機器上)

```bash
# 進入專案目錄
cd /path/to/pdf_rag_mcp

# 安裝依賴
pip install -r server/requirements.txt

# 啟動 Server
./server/start_server.sh
# 或
python -m uvicorn server.rag_server:app --host 0.0.0.0 --port 8000
```

Server 啟動後會顯示：

```
[System] Initializing RAG Server...
[System] 1/2 Loading Embedding Model...
[OK] Model loaded successfully
[System] 2/2 Pre-loading Database...
[System] All systems ready.
```

> 💡 **API 文件**：啟動後訪問 `http://your-server:8000/docs` 可查看 Swagger UI

---

### 步驟 2：設定 Client (在你的電腦上)

1. 修改 `client/start_mcp.bat`，設定 Server 位址：

```batch
set RAG_SERVER_HOST=192.168.1.100   ← 改成你的 Server IP
set RAG_SERVER_PORT=8000
```

2. 安裝 Client 依賴：

```bash
pip install -r client/requirements.txt
```

---

### 步驟 3：設定 Cursor MCP

1. 開啟 Cursor，前往 **Settings** → **MCP**
2. 點擊 **New MCP Server**
3. 填入以下設定：

**名稱**：`Local-Library`

**設定 JSON**：

```json
{
  "mcpServers": {
    "Local-Library": {
      "command": "C:\\你的路徑\\pdf_rag_mcp\\client\\start_mcp.bat",
      "args": []
    }
  }
}
```

> ⚠️ **注意**：請將路徑替換成你實際的位置，路徑中的 `\` 需要寫成 `\\`

---

## 📖 使用範例

### 🔍 查詢知識庫

```
請從知識庫中查詢 XXX 的相關資訊
```

```
根據知識庫，XXX 是什麼意思？
```

### 📁 加入文件到知識庫

```
請把 C:\Documents\report.pdf 加入知識庫
```

**支援的文件格式**：

- 📕 PDF (`.pdf`)
- 📘 Word (`.docx`)
- 📙 PowerPoint (`.pptx`)
- 📗 Excel (`.xlsx`, `.xls`)
- 📄 Markdown (`.md`)
- 📝 純文字 (`.txt`, `.log`)
- 💻 程式碼 (`.py`, `.js`, `.ts`, `.html`, `.css`, `.xml`)
- ⚙️ 設定檔 (`.json`, `.yaml`, `.yml`, `.ini`)

### 📋 列出已索引的文件

```
列出知識庫中已經索引的所有文件
```

---

## 📂 資料夾結構

```
pdf_rag_mcp/
├── server/                    # Server 端
│   ├── rag_server.py          # FastAPI Server
│   ├── requirements.txt       # Server 依賴
│   └── start_server.sh        # 啟動腳本
│
├── client/                    # Client 端
│   ├── mcp_client.py          # MCP Client
│   ├── requirements.txt       # Client 依賴
│   └── start_mcp.bat          # Windows 啟動腳本
│
├── faiss_index/               # 向量索引 (Server 端)
│   ├── index.faiss
│   └── index.pkl
│
├── models/                    # AI 模型快取 (Server 端)
└── README.md
```

---

## 🛠️ Server API

| Endpoint     | Method | Description       |
| ------------ | ------ | ----------------- |
| `/health`    | GET    | 健康檢查          |
| `/documents` | POST   | 新增文件 (Base64) |
| `/documents` | GET    | 列出已索引文件    |
| `/query`     | POST   | 搜尋知識庫        |

### API 範例

**新增文件**：

```bash
curl -X POST http://localhost:8000/documents \
  -H "Content-Type: application/json" \
  -d '{"filename": "test.txt", "content_base64": "SGVsbG8gV29ybGQ="}'
```

**查詢知識庫**：

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "hello"}'
```

---

## 🛠️ MCP 工具清單

| 工具名稱                  | 功能說明                   |
| ------------------------- | -------------------------- |
| `query_library`           | 從知識庫搜尋相關資訊       |
| `add_document_to_library` | 將單個文件加入知識庫       |
| `list_indexed_files`      | 列出已索引的文件及統計資訊 |

---

## ⚙️ 環境變數設定

### Client 端

| 變數                  | 預設值      | 說明               |
| --------------------- | ----------- | ------------------ |
| `RAG_SERVER_HOST`     | `localhost` | Server IP 或主機名 |
| `RAG_SERVER_PORT`     | `8000`      | Server Port        |
| `RAG_REQUEST_TIMEOUT` | `120`       | 請求超時（秒）     |

---

## ❓ 常見問題

### Q: Client 顯示 "Cannot connect to RAG server"？

**A**: 確認：

1. Server 是否已啟動
2. `start_mcp.bat` 中的 IP/Port 設定是否正確
3. 防火牆是否允許該 Port

### Q: 第一次使用 Server 很慢？

**A**: 第一次啟動會下載 AI 模型（約 1GB），後續啟動會快很多。

### Q: 文件太大無法上傳？

**A**: 目前限制單檔 20MB。如需調整，修改 `server/rag_server.py` 中的 `MAX_FILE_SIZE_MB`。

### Q: 如何重置知識庫？

**A**: 停止 Server，刪除 `faiss_index/` 資料夾，重新啟動即可。

### Q: 已索引的文件更新後需要重新加入嗎？

**A**: 是的。目前系統會根據檔名檢測重複，如果檔案內容更新但檔名相同，需要先刪除索引後重新加入。

---

## 🔧 進階設定

### 多 Worker 部署

對於更高的並發需求，可使用多 Worker：

```bash
uvicorn server.rag_server:app --host 0.0.0.0 --port 8000 --workers 4
```

### Docker 部署

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY server/ ./server/
COPY faiss_index/ ./faiss_index/
COPY models/ ./models/

RUN pip install -r server/requirements.txt

EXPOSE 8000
CMD ["uvicorn", "server.rag_server:app", "--host", "0.0.0.0", "--port", "8000"]
```

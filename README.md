

# 📚 Local Library MCP - 本地知識庫搜尋工具

這是一個 **Cursor MCP (Model Context Protocol)** 伺服器，可以讓 Cursor AI 助手直接搜尋你的本地文件知識庫。

> **原理簡介**：將 PDF、Word、Excel、PowerPoint 等文件轉換成向量索引，讓 AI 能夠語意搜尋相關內容。

---

## 🚀 快速開始

### 步驟 1：解壓縮

將整個壓縮檔解壓縮到任意位置，例如：

```
C:\Tools\PDF_RAG_TOOL\
```

### 步驟 2：設定 Cursor MCP

1. 開啟 Cursor，前往 **Settings** → **MCP** (預設畫面右上角的齒輪 -> Cursor Settings -> Tools & MCP)
2. 點擊 **New MCP Server**
3. 填入以下設定：

**名稱**：`Local-Library`（或你喜歡的名稱）

**設定 JSON**：
```json
{
  "mcpServers": {
    "Local-Library": {
      "command": "C:\\你的解壓縮路徑\\PDF_RAG_TOOL\\start_mcp.bat",
      "args": []
    }
  }
}
```

> ⚠️ **注意**：請將 `C:\\你的解壓縮路徑\\` 替換成你實際的解壓縮位置，路徑中的 `\` 需要寫成 `\\`

**完整的 mcp.json 範例**：
```json
{
  "mcpServers": {
    "Local-Library": {
      "command": "C:\\Tools\\PDF_RAG_TOOL\\start_mcp.bat",
      "args": []
    }
  }
}
```

### 步驟 3：重新載入

設定完成後，重新啟動 Cursor 或重新載入 MCP 設定。

---

## 📖 使用範例

### 🔍 查詢知識庫

在 Cursor 聊天視窗中，使用以下關鍵字讓 AI 調用知識庫：

```
請從知識庫中查詢 XXX 的相關資訊
```

```
根據知識庫，XXX 是什麼意思？
```

```
幫我在本地文件中搜尋關於 YYY 的內容
```

> 💡 **提示**：關鍵字如「知識庫」、「本地文件」、「搜尋文件」等可以幫助 AI 理解需要調用 MCP 工具

---

### 📁 加入文件到知識庫

**加入單個文件**：
```
請把 C:\Documents\report.pdf 加入知識庫
```

**批次加入整個資料夾**：
```
請把 C:\MyDocuments\ 資料夾內的所有文件加入知識庫
```

**支援的文件格式**：
- 📕 PDF (`.pdf`)
- 📘 Word (`.docx`)
- 📙 PowerPoint (`.pptx`)
- 📗 Excel (`.xlsx`, `.xls`)

---

### 📋 列出已索引的文件

```
列出知識庫中已經索引的所有文件
```

```
知識庫目前有哪些文件？
```

---

## 🔧 進階操作

### 重置索引（重建知識庫）

如果需要清空知識庫重新建立索引：

1. 關閉 Cursor 或停止 MCP 伺服器
2. 刪除 `faiss_index` 資料夾
3. 重新啟動 Cursor

```
📁 PDF_RAG_TOOL\
├── server.py
├── start_mcp.bat
├── python_env\
└── faiss_index\      ← 刪除這個資料夾即可重置索引
    ├── index.faiss
    └── index.pkl
```

> 刪除後，下次加入文件時會自動建立新的空白索引

---

## 📂 資料夾結構說明

> Note: Documents 只是預設文件，未來使用不需要把檔案複製過來，只要直接給 cursor agent 絕對路徑即可

```
PDF_RAG_TOOL\
├── 📄 server.py          # MCP 伺服器主程式
├── 📄 start_mcp.bat      # 啟動腳本（Cursor 會呼叫這個）
├── 📄 requirements.txt   # Python 依賴套件清單
├── 📁 python_env\        # 內嵌式 Python 環境（已預裝所有套件）
├── 📁 faiss_index\       # 向量索引存放位置
│   ├── index.faiss       # FAISS 索引檔案
│   └── index.pkl         # 文件 metadata
└── 📁 Documents\         # (可選) 範例文件資料夾
```

---

## 🛠️ MCP 工具清單

| 工具名稱 | 功能說明 |
|---------|---------|
| `query_library` | 從知識庫搜尋相關資訊 |
| `add_document_to_library` | 將單個文件加入知識庫 |
| `add_folder_to_library` | 批次將資料夾內所有文件加入知識庫 |
| `list_indexed_files` | 列出已索引的文件及統計資訊 |
| `add_pdf_to_library` | (舊版相容) 等同於 add_document_to_library |

---

## ❓ 常見問題

### Q: 第一次使用很慢怎麼辦？
**A**: 第一次執行時會下載 AI Embedding 模型（約 90MB），這是正常現象。後續使用會快很多。

### Q: 如何確認 MCP 是否正常運作？
**A**: 在 Cursor 聊天視窗問：「知識庫目前有哪些文件？」如果回傳清單或「知識庫是空的」表示運作正常。

### Q: 可以搜尋中文文件嗎？
**A**: 可以！但目前使用的 Embedding 模型（all-MiniLM-L6-v2）對英文效果較佳。中文文件可以索引和搜尋，但語意相關性可能不如英文精準。

### Q: 索引檔案太大怎麼辦？
**A**: `faiss_index` 資料夾的大小會隨著索引的文件數量增加。如果要節省空間，可以刪除不需要的文件後重建索引。

### Q: 已索引的文件更新後需要重新加入嗎？
**A**: 是的。目前系統會根據檔名檢測重複，如果檔案內容更新但檔名相同，需要先刪除 `faiss_index` 資料夾後重新加入。


### Q: MCP Tools 顯示 load error 或是持續 loading tool 怎麼辦?
**A:** 先 disable 再 enable 應該能解決問題。


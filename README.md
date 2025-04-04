# Hybrid Search RAG with FastAPI, Milvus, and WatsonX

This project implements a **Hybrid Search RAG (Retrieval-Augmented Generation)** solution using **FastAPI**, **Milvus**, and **WatsonX**. It supports **BM25 and dense vector search**, integrates with **WatsonX for LLM processing**, and dynamically manages **Milvus collections per user session**.

---

## 📂 Project Structure
```
.
├── bm_wx_openapi_v2.json    # OpenAPI schema for WatsonX integration
├── main.py                  # FastAPI main entry point
├── requirements.txt         # Dependencies list
└── src
    ├── __init__.py          # Package initializer
    ├── milvus_utils.py      # Milvus collection management and search logic
    └── watsonx_utils.py     # WatsonX API integration
```

---

## 🚀 Getting Started

### **1️⃣ Install Dependencies**
Ensure you have Python installed (>=3.8), then install the required packages:
```bash
pip install -r requirements.txt
```

### **2️⃣ Run the FastAPI Server**
Start the FastAPI application:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The API documentation will be available at:
- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- Redoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 🛠 Features
- **Hybrid Search RAG**: Combines BM25 (Lexical Search) with Dense Embeddings (Vector Search)
- **Dynamic Milvus Collection Management**: Creates and drops collections per session
- **FastAPI Integration**: Exposes endpoints for file uploads and hybrid search
- **WatsonX LLM Support**: Generates enriched responses

---

## 📡 API Endpoints
### **1️⃣ Upload Files**
#### **`POST /upload/`**
- **Description**: Uploads PDF files and extracts relevant information.
- **Request Body**:
  ```json
  {
    "files": ["binary file data"],
    "description_input": "Search query"
  }
  ```
- **Response Example**:
  ```json
  {
    "description": "Query Description",
    "relevant_passages": [
      {"text": "Extracted passage from document"}
    ],
    "llm_answer": {
      "llm_final_answer": "Generated answer by WatsonX"
    }
  }
  ```

### **2️⃣ Hybrid Search**
#### **`POST /hybrid_search/`**
- **Description**: Performs a hybrid search combining BM25 and vector search.
- **Request Body**:
  ```json
  {
    "description_input": "Your search query"
  }
  ```
- **Response**: Ranked passages with WatsonX-generated insights.

---

## 🏗️ Project Components
### **🔹 `milvus_utils.py`**
- Handles Milvus operations (creating/dropping collections, inserting/searching vectors).
- Uses `sentence-transformers/all-MiniLM-L6-v2` for text embeddings.

### **🔹 `watsonx_utils.py`**
- Manages API calls to WatsonX for LLM-based question answering.
- Formats and structures responses.

---

## 🛠 Future Improvements
- 🔹 **Integrate additional embedding models**
- 🔹 **Optimize text chunking strategies**
- 🔹 **Implement authentication & user session tracking**

---


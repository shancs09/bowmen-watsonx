# 🚀 Hybrid RAG API with FastAPI, Milvus & WatsonX

This project implements a **Hybrid Search RAG (Retrieval-Augmented Generation)** solution using **FastAPI**, **Milvus**, and **WatsonX**. It supports **BM25 and dense vector search**, integrates with **WatsonX for LLM processing**, and dynamically manages **Milvus collections per user session**.

                        ┌─────────────────────────────┐
                        │         End User            │
                        │  (via Swagger or API call)  │
                        └────────────┬────────────────┘
                                     │
                          [1] Upload PDF / Query
                                     │
                             ┌───────▼────────┐
                             │    FastAPI     │  ◄──────────────┐
                             │  (Code Engine) │                 │
                             └───────┬────────┘                 │
                                     │                          │
          ┌──────────────────────────▼────────────────────────┐ │
          │               Text Chunking &                     │ │
          │     Embedding Generation (SentenceTransformer /   │ │
          │     WatsonX Embeddings SDK based on mode)         │ │
          └────────────────┬──────────────────────────────────┘ │
                           │                                    │
           [2a] BM25       │        [2b] Dense Embeddings       │
     Keyword Matching      │        (WatsonX or SBERT)          │
                           │                                    │
                   ┌───────▼────────┐               ┌────────── ▼─────────┐
                   │   BM25 Index   │               │   Milvus Vector DB  │
                   │ (In-Memory)    │               │ (Cloud VM-hosted)   │
                   └───────────────┬┘               └─────────────────────┘
                                   │                              
                           [3] Hybrid Search & RRF Ranking       
                                   │                              
                            ┌──────▼───────┐
                            │   Top-k Passages                    
                            └──────┬───────┘
                                   │
                            [4] Prompt Construction
                                   │
                      ┌────────────▼─────────────┐
                      │    IBM WatsonX LLM API   │
                      │     (Text Generation)    │
                      └────────────┬─────────────┘
                                   │
                             [5] Final Response
                                   │
                       ┌───────────▼────────────┐
                       │  Hybrid Search Output  │
                       │  + LLM Generated Answer│
                       └────────────────────────┘

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

## 🐳 Run with Docker

### **1️⃣ Build the Docker Image**
```bash
docker build -t bw_soc_wx_hybrid_search .
```

### **2️⃣ Run the Container**
```bash
docker run -d -p 8000:8000 bw_soc_wx_hybrid_search
```

Access the app at: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## ☁️ Deployment (IBM Cloud Code Engine)

The FastAPI app can be containerized and deployed to IBM Cloud Code Engine:

- ✅ Push the image to IBM Cloud Container Registry (`uk.icr.io/...`)
- ✅ Deploy as a Code Engine app using the container image
- ✅ Ensure Milvus (running on IBM Cloud VM) is publicly reachable

Live Endpoint: [https://bw-wx-hybrid-search.1tyxjp422ztp.eu-gb.codeengine.appdomain.cloud/docs](https://bw-wx-hybrid-search.1tyxjp422ztp.eu-gb.codeengine.appdomain.cloud/docs)

---

## 🛠 Features
- **Hybrid Search RAG**: Combines BM25 (Lexical Search) with Dense Embeddings (Vector Search)
- **Dynamic Milvus Collection Management**: Creates and drops collections per session
- **FastAPI Integration**: Exposes endpoints for file uploads and hybrid search
- **WatsonX LLM Support**: Uses IBM WatsonX LLMs to generate enriched responses

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

## 🔍 Quick Example
```bash
curl -X POST http://localhost:8000/hybrid_search/ \
  -H "Content-Type: application/json" \
  -d '{"description_input": "What is zero trust architecture?"}'
```

---

## 🛠 Future Improvements
- 🔹 **Integrate additional embedding models**
- 🔹 **Optimize text chunking strategies**
- 🔹 **Implement authentication & user session tracking**


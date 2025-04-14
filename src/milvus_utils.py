import os,numpy as np,fitz,time
from pymilvus import MilvusClient, DataType, Function, FunctionType,AnnSearchRequest, RRFRanker
from src.watsonx_utils import wx_embeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Load environment variables
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
MILVUS_HOST = os.getenv("MILVUS_HOST")
MILVUS_PORT = os.getenv("MILVUS_PORT")
MILVUS_USERNAME = os.getenv('MILVUS_USERNAME')
MILVUS_PASSWORD = os.getenv('MILVUS_PASSWORD')
# COLLECTION_NAME = os.getenv("COLLECTION_NAME", "demo")

# # Initialize embedding model
# embedding_model = SentenceTransformer(EMBEDDING_MODEL)

# # Initialize Milvus client
# def get_milvus_client():
#     token = f"{MILVUS_USERNAME}:{MILVUS_PASSWORD}"
#     return MilvusClient(uri=f"http://{MILVUS_HOST}:{MILVUS_PORT}", token=token)

token = f"{MILVUS_USERNAME}:{MILVUS_PASSWORD}"
client = MilvusClient(
    uri=f"http://{MILVUS_HOST}:{MILVUS_PORT}",
    token=token
)
def create_schema_collection(collection_name):
    if collection_name in client.list_collections():
        print(f"Collection '{collection_name}' already exists.")
        drop_collection(collection_name)
        # return
    
    schema = client.create_schema()
    schema.add_field("id", DataType.INT64, is_primary=True, auto_id=True)
    schema.add_field("filename", DataType.VARCHAR, max_length=255)
    schema.add_field("text", DataType.VARCHAR, max_length=1000, enable_analyzer=True)
    schema.add_field("dense", DataType.FLOAT_VECTOR, dim=384)
    schema.add_field("sparse", DataType.SPARSE_FLOAT_VECTOR)

    bm25_function = Function(
        name="text_bm25_emb",
        input_field_names=["text"],
        output_field_names=["sparse"],
        function_type=FunctionType.BM25,
    )
    schema.add_function(bm25_function)

    index_params = client.prepare_index_params()
    index_params.add_index("dense", index_type="AUTOINDEX", metric_type="COSINE")
    index_params.add_index("sparse", index_type="SPARSE_INVERTED_INDEX", metric_type="BM25")

    client.create_collection(collection_name, schema=schema, index_params=index_params)

def chunk_text(text, chunk_size=500, chunk_overlap=50):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len
    )
    print("Chunk text completed")
    return splitter.split_text(text)

def extract_text_from_pdf(pdf_content: bytes):
    doc = fitz.open(stream=pdf_content, filetype="pdf")
    text = "\n".join([page.get_text("text") for page in doc])
    print("Extraction text from PDF Completed")
    return text


async def data_ingestion(pdf_content: bytes,collection_name: str,filename: str):
    # client = get_milvus_client()
    text = extract_text_from_pdf(pdf_content)
    if not text.strip():  # Handle empty PDFs gracefully
        print(f"Skipping ingestion: No text found in PDF for {collection_name}")
        return None
    chunks = chunk_text(text)
    # Batch Mode
    BATCH_SIZE = 1000

    for i in range(0, len(chunks), BATCH_SIZE):
        batch_chunks = chunks[i:i+BATCH_SIZE]
        t0 = time.time()
        
        # 1. Generate embeddings using Watsonx
        batch_embeddings = wx_embeddings.embed_documents(batch_chunks)
        print(f"[EMBEDDING] {filename}: Batch {i//BATCH_SIZE + 1} took {time.time() - t0:.2f}s")

        # 2. Convert to numpy and then tolist() if needed for Milvus
        batch_embeddings = np.array(batch_embeddings).tolist()
        records = [ {'filename': filename, 'text': chunk, 'dense': vec} for chunk, vec in zip(batch_chunks, batch_embeddings)]
        client.insert(collection_name, records)

    print(f"DATA INGESTION COMPLETED for {filename} in {collection_name}")
    # client.close()
    return None

def hybrid_search(query: str, collection_name: str):
    # client = get_milvus_client()
    # query_dense_vector = embedding_model.encode([query], convert_to_numpy=True).tolist()
    query_dense_vector = [wx_embeddings.embed_query(query)]

    request_1 = AnnSearchRequest(
        data=query_dense_vector,
        anns_field="dense",
        param={"metric_type": "COSINE"},
        limit=3
    )

    request_2 = AnnSearchRequest(
        data=[query],
        anns_field="sparse",
        param={"metric_type": "BM25", "params": {"drop_ratio_build": 0.0}},
        limit=3
    )

    ranker = RRFRanker()
    results = client.hybrid_search(
        collection_name=collection_name,
        output_fields=['text','filename'],
        reqs=[request_1, request_2],
        ranker=ranker,
        limit=3
    )
    # client.close()
    # close_client() # Close client after search to prevent too many open connections
    return results

def extract_passages(search_results):
    """Extracts passages and distance scores from search results."""
    evidences=[
            {
                "text": hit['entity']['text'],
                "filename": hit['entity']['filename'],  # ✅ Include filename
                "distance": hit['distance']
            } 
            for hit in search_results[0]
        ]
    return evidences
    # return {"passages": [{"text": hit['entity']['text'], "distance": hit['distance']} for hit in search_results[0]]}

def clean_data(collection_name: str):
    # client = get_milvus_client()
    client.delete(collection_name=collection_name, filter="id > 0")
    # client.close()
    print(f"All data from collection '{collection_name}' has been deleted.")

def drop_collection(collection_name: str):
    # client = get_milvus_client()
    client.drop_collection(collection_name)
    # client.close()
    print(f"Collection '{collection_name}' has been dropped.")

# def close_client():
#     print("Closing Milvus client connection...")
#     client.close()
#     print("Milvus client connection closed.")

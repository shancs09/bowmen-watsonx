import os
import uvicorn
import json
from fastapi import FastAPI, File, UploadFile, Form,Query
from typing import  List, Dict, Any
from pydantic import BaseModel
from src.milvus_utils import client,create_schema_collection, data_ingestion, hybrid_search, extract_passages,drop_collection
from src.watsonx_utils import inference_llm,wx_embeddings
import uuid
from concurrent.futures import ThreadPoolExecutor
import asyncio

# Initialize FastAPI app
app = FastAPI()

#New Schema Update:
# 🔹 Upload Request Schema
class ControlItem(BaseModel):
    test_control: str
    test_plan: str
    description: str
    resource_id: str

class ControlInput(BaseModel):
    controls_data: List[ControlItem]

# 🔹 Relevant Passages
class Passage(BaseModel):
    text: str
    filename: str
    distance: float

# 🔹 LLM Answer structure
class LLMAnswer(BaseModel):
    Compliance_Status: str
    llm_final_answer: str
    explanation: str
    source: str
    gap_analysis: str
    confidence_score: float


# 🔹 Response Item per control
class ResponseItem(BaseModel):
    test_control: str
    test_plan: str
    description: str
    resource_id: str
    relevant_passages: List[Passage]
    llm_answer: LLMAnswer

# 🔹 Final Upload Response
class UploadResponse(BaseModel):
    collection_name: str
    controls_data: List[ResponseItem]

def safe_llm_answer(data: dict) -> LLMAnswer:
    """Cleans and safely maps a dict to the LLMAnswer model."""
    cleaned = data.copy()
    
    # Ensure 'source' is a string
    source = cleaned.get("source")
    if isinstance(source, list):
        cleaned["source"] = ", ".join(str(s) for s in source)  # join list into string
    elif source is None:
        cleaned["source"] = ""

    # Set defaults for missing or invalid fields
    cleaned.setdefault("Compliance_Status", "Unknown")
    cleaned.setdefault("llm_final_answer", "")
    cleaned.setdefault("explanation", "")
    cleaned.setdefault("gap_analysis", "")
    cleaned.setdefault("confidence_score", 0.0)

    return LLMAnswer(**cleaned)


def format_context(extracted_passages):
    formatted_text = ""

    # Group passages by filename
    passages_by_file = {}
    for passage in extracted_passages:
        filename = passage.get("filename", "Unknown File")  # Handle missing filenames
        text = passage["text"]
        
        if filename not in passages_by_file:
            passages_by_file[filename] = []
        
        passages_by_file[filename].append(text)

    # Format into "Filename: \n text1 \n text2 \n\n" structure
    formatted_text = "\n\n".join(
        f"Filename: {filename}\n\n" + "\n".join(texts) for filename, texts in passages_by_file.items()
    )
    return formatted_text

# @app.post("/upload/", response_model=UploadResponse)
# async def upload_files(
#     files: List[UploadFile] = File(..., description="Upload PDF files"),
#     description_input: str = Form(..., description="Description JSON input"),
#     auto_drop_collection_after_search: bool = Query(True, description="Drop collection after search")
# ):
#     collection_name = f"session_{uuid.uuid4().hex}"
    
#     #Data Ingestion
#     file_contents = {}
#     for file in files:
#         content = await file.read()
#         file_contents[file.filename] = content
#     print("FILE CONTENT READ")

#     # Ensure Milvus collection exists
#     create_schema_collection(collection_name)

#     for file_name, content in file_contents.items():
#         data_ingestion(pdf_content=content,collection_name=collection_name,filename=file_name)
#         print(f"Ingested {file_name} into collection {collection_name}")

#     #Retrieval
#     try:
#         description_dict = json.loads(description_input)
#         # descriptions = description_dict.get("descriptions", [])
#         control_input = ControlInput.parse_obj(description_dict)
#     except Exception as e:
#         return {"error": "Invalid JSON provided in description_input", "detail": str(e)}
#     print("DECRIPTION EXTRACTED:")
#     response_data=[]
#     for control in control_input.controls_data:
#         desc = control.description
#         search_results = hybrid_search(desc,collection_name)
#         extracted_passages = extract_passages(search_results) 
#         llm_context =format_context(extracted_passages)
#         # Invoke Watsonx for LLM response using description & relevant passages
#         watsonx_response = inference_llm(llm_context, desc)
#         print(watsonx_response)
#         # Build the structured response
#         response_item = ResponseItem(
#             test_control=control.test_control,
#             test_plan=control.test_plan,
#             resource_id=control.resource_id,
#             description=desc,
#             relevant_passages=[Passage(**p) for p in extracted_passages],
#             llm_answer=LLMAnswer(**watsonx_response)
#         )
#         response_data.append(response_item)

#     if auto_drop_collection_after_search:
#         drop_collection(collection_name)
#     return UploadResponse(collection_name=collection_name,controls_data=response_data)

def process_control(control, collection_name):
    desc = control.description
    search_results = hybrid_search(desc, collection_name)
    extracted_passages = extract_passages(search_results)
    llm_context = format_context(extracted_passages)

    # Call Watsonx LLM
    watsonx_response = inference_llm(llm_context, desc)
    print(watsonx_response)

    # Parse and package
    llm_answer = safe_llm_answer(watsonx_response)
    return ResponseItem(
        test_control=control.test_control,
        test_plan=control.test_plan,
        resource_id=control.resource_id,
        description=desc,
        relevant_passages=[Passage(**p) for p in extracted_passages],
        llm_answer=llm_answer
    )
@app.post("/upload/", response_model=UploadResponse)
async def upload_files(
    files: List[UploadFile] = File(..., description="Upload PDF files"),
    description_input: str = Form(..., description="Description JSON input"),
    auto_drop_collection_after_search: bool = Query(True, description="Drop collection after search")
):
    collection_name = f"session_{uuid.uuid4().hex}"
    
    # Ensure Milvus collection exists
    create_schema_collection(collection_name)

    # Read files concurrently
    file_contents = {file.filename: await file.read() for file in files}
    print("FILE CONTENT READ")

    # Use asyncio.gather to run ingestion in parallel
    tasks = [
        data_ingestion(pdf_content=content, collection_name=collection_name, filename=filename)
        for filename, content in file_contents.items()
    ]
    await asyncio.gather(*tasks)
     # Flush once after all ingestion is done
    client.flush(collection_name)

    #Retrieval
    try:
        description_dict = json.loads(description_input)
        # descriptions = description_dict.get("descriptions", [])
        control_input = ControlInput.parse_obj(description_dict)
    except Exception as e:
        return {"error": "Invalid JSON provided in description_input", "detail": str(e)}
    print("DECRIPTION EXTRACTED:")
    response_data=[]
    # inside your route...
    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor() as executor:
        tasks = [
            loop.run_in_executor(executor, process_control, control, collection_name)
            for control in control_input.controls_data
        ]
        response_data = await asyncio.gather(*tasks)
    if auto_drop_collection_after_search:
        drop_collection(collection_name)
    return UploadResponse(collection_name=collection_name,controls_data=response_data)

# @app.post("/create_collection/")
# async def create_collection(
#     files: List[UploadFile] = File(..., description="Upload PDF files")
# ):
#     collection_name = f"session_{uuid.uuid4().hex}"
    
#     # Ensure Milvus collection exists
#     create_schema_collection(collection_name)

#     #Data Ingestion
#     file_contents = {}
#     for file in files:
#         content = await file.read()
#         file_contents[file.filename] = content
#     print("FILE CONTENT READ")

#     # for file_name, content in file_contents.items():
#     #     data_ingestion(pdf_content=content,collection_name=collection_name,filename=file_name)
#     #     print(f"Ingested {file_name} into collection {collection_name}")
#     # # Ingest in parallel using process pool
#     # loop = asyncio.get_running_loop()
#     # tasks = []
#     # with ProcessPoolExecutor() as executor:
#     #     for file_name, content in file_contents.items():
#     #         tasks.append(loop.run_in_executor(
#     #             executor,
#     #             data_ingestion,
#     #             content,
#     #             collection_name,
#     #             file_name
#     #         ))
#     #     await asyncio.gather(*tasks)
#     loop = asyncio.get_running_loop()
#     tasks = []
#     with ThreadPoolExecutor() as executor:
#         for file_name, content in file_contents.items():
#             tasks.append(loop.run_in_executor(
#                 executor,
#                 data_ingestion,
#                 content,
#                 collection_name,
#                 file_name
#             ))
#         await asyncio.gather(*tasks)

#     return {"collection_name":{collection_name},"response":"Data Ingestion sucessfull"}

@app.post("/create_collection/")
async def create_collection(
    files: List[UploadFile] = File(..., description="Upload PDF files")
):
    collection_name = f"session_{uuid.uuid4().hex}"
    
    # Ensure Milvus collection exists
    create_schema_collection(collection_name)

    # Read files concurrently
    file_contents = {file.filename: await file.read() for file in files}
    print("FILE CONTENT READ")

    # Use asyncio.gather to run ingestion in parallel
    tasks = [
        data_ingestion(pdf_content=content, collection_name=collection_name, filename=filename)
        for filename, content in file_contents.items()
    ]
    await asyncio.gather(*tasks)
     # Flush once after all ingestion is done
    client.flush(collection_name)
    return {"collection_name": collection_name, "response": "Data Ingestion successful"}


# @app.post("/llm_watsonx_answer/", response_model=UploadResponse)
# async def llm_watsonx_answer(hybrid_search_response: dict):

#     collection_name = hybrid_search_response.get("collection_name")
#     responses = hybrid_search_response.get("controls_data", [])
    
#     llm_response = []
#     for resp in responses:
#         description = resp.get("description", "")
#         test_control = resp.get("test_control", "")
#         test_plan = resp.get("test_plan", "")
#         resource_id = resp.get("resource_id", None)  # Optional, only if used
#         extracted_passages = resp.get("relevant_passages", [])

#         # Format passages for WatsonX input
#         llm_context = format_context(extracted_passages)
#         # Invoke WatsonX for LLM response
#         watsonx_response = inference_llm(llm_context, description)
#         # Append results
#         response_item = ResponseItem(
#                 test_control=test_control,
#                 test_plan=test_plan,
#                 resource_id=resource_id,
#                 description=description,
#                 relevant_passages=[Passage(**p) for p in extracted_passages],
#                 llm_answer=LLMAnswer(**watsonx_response)
#             )
#         llm_response.append(response_item)
#     return UploadResponse(collection_name=collection_name, controls_data=llm_response)

@app.post("/llm_watsonx_answer/", response_model=UploadResponse)
async def llm_watsonx_answer(hybrid_search_response: dict):
    collection_name = hybrid_search_response.get("collection_name")
    responses = hybrid_search_response.get("controls_data", [])

    def wx_process_response(resp):
        description = resp.get("description", "")
        test_control = resp.get("test_control", "")
        test_plan = resp.get("test_plan", "")
        resource_id = resp.get("resource_id", None)
        extracted_passages = resp.get("relevant_passages", [])

        llm_context = format_context(extracted_passages)
        watsonx_response = inference_llm(llm_context, description)

        return ResponseItem(
            test_control=test_control,
            test_plan=test_plan,
            resource_id=resource_id,
            description=description,
            relevant_passages=[Passage(**p) for p in extracted_passages],
            llm_answer=safe_llm_answer(watsonx_response)  # Optional: add safety wrapper here too
        )

    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor() as executor:
        tasks = [
            loop.run_in_executor(executor, wx_process_response, resp)
            for resp in responses
        ]
        llm_response = await asyncio.gather(*tasks)

    return UploadResponse(collection_name=collection_name, controls_data=llm_response)


@app.post("/hybrid_search_by_collection/")
async def hybrid_search_by_collection(
    collection_name: str,
    description_input: str = Form(..., description="Description JSON input")
):
    try:
        description_dict = json.loads(description_input)
        control_input = ControlInput.parse_obj(description_dict)
    except Exception as e:
        return {"error": "Invalid JSON provided in description_input", "detail": str(e)}

    def hs_process_control(control):
        desc = control.description
        search_results = hybrid_search(desc, collection_name)
        extracted_passages = extract_passages(search_results)

        return {
            "test_control": control.test_control,
            "test_plan": control.test_plan,
            "resource_id": control.resource_id,
            "description": desc,
            "relevant_passages": extracted_passages
        }

    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor() as executor:
        tasks = [
            loop.run_in_executor(executor, hs_process_control, control)
            for control in control_input.controls_data
        ]
        response = await asyncio.gather(*tasks)

    return { "collection_name": collection_name, "controls_data": response }

# @app.post("/hybrid_search_by_collection/")
# async def hybrid_search_by_collection(collection_name: str,
#     description_input: str = Form(..., description="Description JSON input")
# ):
#     try:
#         description_dict = json.loads(description_input)
#         control_input = ControlInput.parse_obj(description_dict)
#     except Exception as e:
#         return {"error": "Invalid JSON provided in description_input", "detail": str(e)}
    
#     response = []
#     for control in control_input.controls_data:
#         desc = control.description
#         search_results = hybrid_search(desc, collection_name)
#         extracted_passages = extract_passages(search_results)

#         response.append({
#             "test_control": control.test_control,
#             "test_plan": control.test_plan,
#             "resource_id": control.resource_id,
#             "description": desc,
#             "relevant_passages": extracted_passages
#         })

#     return { "collection_name": collection_name,"controls_data": response}


@app.post("/drop_collection/")
async def drop_collection_by_name(collection_name: str):
    try:
        client.drop_collection(collection_name)
        return {"message": f"Collection '{collection_name}' has been dropped successfully."}
    except Exception as e:
        return {"error": f"Failed to drop collection '{collection_name}'", "detail": str(e)}


@app.post("/drop_all_collections/")
async def drop_all_collections():
    collections = client.list_collections()
    if not collections:
        return {"message": "No collections found in Milvus."}

    for collection_name in collections:
        try:
            drop_collection(collection_name)
        except Exception as e:
            print(f"Failed to drop collection '{collection_name}': {str(e)}")

    return {"message": "All collections have been dropped successfully."}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))  # <-- use env PORT if available
    uvicorn.run(app, host="0.0.0.0", port=port)
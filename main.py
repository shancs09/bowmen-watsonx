import os
import uvicorn
import json
from fastapi import FastAPI, File, UploadFile, Form,Query
from typing import  List, Dict, Any
from pydantic import BaseModel
from src.milvus_utils import client,create_schema_collection, data_ingestion, hybrid_search, extract_passages,drop_collection
from src.watsonx_utils import inference_llm

import uuid

# Initialize FastAPI app
app = FastAPI()

#Upload request schema
class Field(BaseModel):
    name: str
    value: str

class Row(BaseModel):
    fields: List[Field]

class DescriptionInput(BaseModel):
    rows: List[Row]

#Upload response schema

class ResponseItem(BaseModel):
    description: str
    relevant_passages: List[Dict[str, Any]]
    llm_answer: Dict[str, Any]

class UploadResponse(BaseModel):
    collection_name: str
    response: List[ResponseItem]

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

    print(formatted_text) 
    return formatted_text

@app.post("/upload/", response_model=UploadResponse)
async def upload_files(
    files: List[UploadFile] = File(..., description="Upload PDF files"),
    description_input: str = Form(..., description="Description JSON input"),
    auto_drop_collection_after_search: bool = Query(True, description="Drop collection after search")
):
    collection_name = f"session_{uuid.uuid4().hex}"
    
    #Data Ingestion
    file_contents = {}
    for file in files:
        content = await file.read()
        file_contents[file.filename] = content
    print("FILE CONTENT READ")

    # Ensure Milvus collection exists
    create_schema_collection(collection_name)

    for file_name, content in file_contents.items():
        data_ingestion(pdf_content=content,collection_name=collection_name,filename=file_name)
        print(f"Ingested {file_name} into collection {collection_name}")

    #Retrieval
    try:
        description_dict = json.loads(description_input)
        # descriptions = description_dict.get("descriptions", [])
        description_parsed = DescriptionInput.parse_obj(description_dict)
    except Exception as e:
        return {"error": "Invalid JSON provided in description_input", "detail": str(e)}
    print("DECRIPTION EXTRACTED:")
    descriptions = [
        field.value 
        for row in description_parsed.rows 
        for field in row.fields 
        if field.name == "Description"
    ]
    print(descriptions)
    # response = []
    response_data=[]
    for desc in descriptions:
        search_results = hybrid_search(desc,collection_name)
        extracted_passages = extract_passages(search_results) 
        llm_context =format_context(extracted_passages)
        # Invoke Watsonx for LLM response using description & relevant passages
        watsonx_response = inference_llm(llm_context, desc)
        # Append results along with LLM answer
        # response.append({
        #     "description": desc,
        #     "relevant_passages": extracted_passages,  # Keeping original for reference
        #     "llm_answer": watsonx_response  # Adding the Watsonx response here
        # })
        response_data.append(ResponseItem(
            description=desc,
            relevant_passages=extracted_passages,
            llm_answer=watsonx_response
        ))
        # response.append({"description": desc, "relevant_passages": extract_passages(search_results)})

    if auto_drop_collection_after_search:
        drop_collection(collection_name)
    # return {"collection_name":collection_name,"response": response}
    return  UploadResponse(collection_name=collection_name, response=response_data)

@app.post("/llm_watsonx_answer/", response_model=UploadResponse)
async def llm_watsonx_answer(hybrid_search_response: dict):

    collection_name = hybrid_search_response.get("collection_name")
    responses = hybrid_search_response.get("response", [])
    
    llm_response = []
    for resp in responses:
        description = resp.get("description", "")
        extracted_passages = resp.get("relevant_passages", [])

        # Format passages for WatsonX input
        llm_context = format_context(extracted_passages)
        # Invoke WatsonX for LLM response
        watsonx_response = inference_llm(llm_context, description)
        # Append results
        llm_response.append(ResponseItem(
            description=description,
            relevant_passages=extracted_passages,
            llm_answer=watsonx_response
        ))
        # llm_response.append({
        #     "description": description,
        #     "relevant_passages": extracted_passages,
        #     "llm_answer": watsonx_response  
        # })
    return UploadResponse(collection_name=collection_name, response=llm_response)

    # return {"collection_name": collection_name, "response": llm_response}


    
@app.post("/hybrid_search_by_collection/")
async def hybrid_search_by_collection(collection_name: str,
    description_input: str = Form(..., description="Description JSON input")
):
   
    try:
        description_dict = json.loads(description_input)
        description_parsed = DescriptionInput.parse_obj(description_dict)
    except Exception as e:
        return {"error": "Invalid JSON provided in description_input", "detail": str(e)}
    descriptions = [
        field.value 
        for row in description_parsed.rows 
        for field in row.fields 
        if field.name == "Description"
    ]
    print(descriptions)
    response = []
    for desc in descriptions:
        search_results = hybrid_search(desc,collection_name)
        extracted_passages = extract_passages(search_results) 
        response.append({"description": desc, "relevant_passages": extracted_passages})
    
    return {"collection_name":collection_name,"response": response}


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
    uvicorn.run(app, host="0.0.0.0", port=8000)
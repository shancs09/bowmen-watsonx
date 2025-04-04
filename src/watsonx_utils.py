
from dotenv import load_dotenv
import re,os,json
from ibm_watsonx_ai import Credentials
from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams
from ibm_watsonx_ai.foundation_models.utils.enums import ModelTypes, DecodingMethods


# Load environment variables from .env file (if using dotenv for environment variables)
load_dotenv()

wx_api_key = os.getenv('wx_api_key')
wx_service_url = os.getenv('wx_service_url')
wx_project_id = os.getenv('wx_project_id')
wx_llm_model_id = os.getenv('wx_llm_model_id', 'mistralai/mixtral-8x7b-instruct-v01')  # Default value in case ENV is missing

# To display example params enter # print(GenParams().get_example_values())
generate_params = {
    GenParams.DECODING_METHOD:'greedy',
    GenParams.MAX_NEW_TOKENS: 5000,
    GenParams.STOP_SEQUENCES:["}\n"]
}

model_inference = ModelInference(
    model_id=wx_llm_model_id, # Using utils: ModelTypes.MIXTRAL_8X7B_INSTRUCT_V01
    credentials=Credentials(
        api_key = wx_api_key,
        url = wx_service_url),
        project_id=wx_project_id
    )

def inference_llm(context_passages,question):
    # Define the input prompt
    llm_instr = """
    <s>[INST] <<SYS>>  
    You are a helpful, respectful, and honest AI compliance assistant leveraging Retrieval-Augmented Generation (RAG). Your primary objective is to analyze the document and verify whether the given compliance control is addressed. Your responses must be strictly fact-based, using only the provided documents.  

    ### **Response Guidelines:**  
    - **DO NOT** generate assumptions or infer details beyond the provided documents.  
    - **DO NOT** provide an answer if relevant information is missing—explicitly state that the document does not contain the required details.  
    - **DO NOT** change the expected output structure—your response **MUST** strictly follow the predefined JSON format.  
    - **ALWAYS** include document references to support your answer, using section titles or numbers if available.  
    - **ENSURE** that your final output is structured correctly in **valid JSON format**, without additional text or explanations outside of JSON.  

    ### **Task Instructions:**  
    1. **Search** for content in the document that closely matches the provided compliance control.  
    2. **Extract** relevant text from the document that aligns with the compliance requirement.  
    3. **Analyze** whether the extracted content fully, partially, or fails to support compliance.  
    4. **Highlight** any gaps or missing details if the control is not fully addressed.  
    5. **Provide** a **confidence score (0 to 100)** indicating how well the extracted information matches the compliance requirement.  
    6. **Determine** the compliance status as either:  
    - "Determined" → If relevant content is found.  
    - "Not Determined" → If no relevant content is found.  
    7. **Generate** the final structured response strictly in the following JSON format:  

    ### **Expected JSON Output Format:**  
    ```json
    {{
    "Compliance Status": "<Determined | Not Determined>",
    "llm_final_answer": "<Summarized compliance assessment>",
    "explanation": "<Detailed explanation of findings>",
    "source": "<Exact document name or section or title used to arrive llm final answer>",
    "gap_analysis": "<Identify missing details, if any>",
    "confidence_score": <Integer between 0-100>
    }}
    ```

    ### **Context for Compliance Evaluation:**  
    - **Reference Documents:**  
    {doc_snippet}
    - **User Question:** `{question}`  

    **Your response must always be structured strictly in the JSON format above.**  
    Failure to follow this structure will result in rejection.  
    <</SYS>>  

    UserQuestion: {question}  
    Output: 
    </s>
    """

    # Format the prompt dynamically
    formatted_prompt = llm_instr.format(
        doc_snippet=context_passages,
        question=question
    )
    # formatted_prompt = f"""{llm_instr}""".replace("{doc_snippet}", context_passages).replace("{question}", question)

    # print(formatted_prompt)
    generated_response = model_inference.generate(prompt=formatted_prompt,params=generate_params)
    # print(generated_response)
    # print(generated_response['results'][0]['generated_text'])
    llm_response=generated_response['results'][0]['generated_text']
    print(type(llm_response))
    # Extract structured JSON from response
    llm_json_response = extract_json(llm_response)
    print(llm_json_response)
    return llm_json_response


def extract_json(output_text):
    """Extract JSON object from LLM output."""
    json_match = re.search(r'\{.*?\}|\[.*?\]', output_text, re.DOTALL)
    
    if json_match:
        try:
            json_object = json.loads(json_match.group(0))
            if isinstance(json_object, list) and len(json_object) > 0:
                return json_object[0]  # Return first element if list
            return json_object  # Otherwise, return dictionary
        except json.JSONDecodeError:
            return {"error": "Invalid JSON format", "original_output": output_text}
    else:
        return {"error": "No JSON object found", "original_output": output_text}  



# Run the application
if __name__ == "__main__":    

    llm_context=f"Filename: Microsoft 365 - SOC 1 Type 1 Report  (05-15-2024).pdf\n\nenvironment.  \nData Classification \nDefinition \nAccess Control Data \nData used to manage access to administrative roles or sensitive functions. \nCustomer Content \nContent directly created by users. Content is not viewed by Microsoft personnel \nunless required to resolve a ticketed service problem. \nEnd User Identifiable \nInformation (EUII) \nData unique to a user or generated from a user’s use of the service:  \n• Linkable to an individual user  \n• Does not contain customer content\n\nFilename: Azure - IRIS ICCS & ICP SOC 2 Type 1 Report (2018).pdf.pdf\n\nencryption key is restricted to authorized individuals. \nCCL-72 – Services Production environment uses different encryption keys than those for the Pre-Production \nenvironment (PPE).  \nCCL-98 – The Production and Pre-Production environment (PPE) are separated. New features and major \nchanges are developed and tested in separate environments prior to production implementation. Production \ndata is not replicated in test or development environments.\n\nFilename: Microsoft General - NGP PIMS SSAE 18 SOC 2 Report.pdf\n\nService auditors’ report for Microsoft NGP-PIMS - Page 11 \nData  \nData is maintained in Azure services and server databases. Each service team and support team is \nresponsible for managing security and availability of the data on the database servers. Reference the table \nbelow for the defined data classifications for this report and the NGP-PIMS environment.  \nData classification \nDefinition \nAccess control data \nData used to manage access to administrative roles or sensitive functions"
    question="Encrypt all non-console administrative access. Use technologies such as SSH, VPN, or SSL/TLS for web-based management and other non-console administrative access."
    print(inference_llm(llm_context,question))
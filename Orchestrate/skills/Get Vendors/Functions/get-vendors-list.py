import json  # Needed to convert data to a JSON string
import os
import http.client
import urllib.parse

def get_access_token():
    TOKEN_URL = "iam.cloud.ibm.com"
    API_KEY = os.getenv("API_KEY")

    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = urllib.parse.urlencode({
        "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
        "apikey": API_KEY
    })

    try:
        conn = http.client.HTTPSConnection(TOKEN_URL)
        conn.request("POST", "/identity/token", body=data, headers=headers)
        response = conn.getresponse()
        if response.status != 200:
            print(f"Error fetching access token: {response.status} {response.reason}")
            return None
        data = json.loads(response.read().decode())
        return data.get("access_token")
    except Exception as e:
        print(f"Error fetching access token: {e}")
        return None
    finally:
        conn.close()

def transform_json(input_json):
    transformed_data = {"body": {"hwtable": []}}
    
    for row in input_json["rows"]:
        row_dict = {}
        for field in row["fields"]:
            if field["name"] == "Name":
                row_dict["vendor"] = field["value"]
            elif field["name"] == "Description":
                row_dict["description"] = field["value"]
        
        if row_dict:  # Ensure row_dict is not empty
            transformed_data["body"]["hwtable"].append(row_dict)
    
    return transformed_data
    
def main(params):
    token = get_access_token()
    
    # API endpoint details for OpenPages query
    host = "a67919ef-db35-4266-acc2-0d47bfe4aa06.eu-central-1.aws.openpages.ibm.com"
    endpoint = "/opgrc/api/v2/query/"
    
    # Headers
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    # Data payload
    query_payload = json.dumps({
        "statement": "SELECT [Resource ID],[Name], [Description] FROM [Vendor]",
        "offset": 0,
        "max_rows": 0,
        "limit": 50,
        "case_insensitive": False,
        "honor_primary": False
    })
    
    # Create connection
    conn = http.client.HTTPSConnection(host)
    conn.request("POST", endpoint, body=query_payload, headers=headers)
    response = conn.getresponse()
    
    responseJSON = ""
    # Check response
    if response.status in (200, 201):
        responseJSON = json.loads(response.read().decode())
    else:
        responseJSON = {"Error": "Error occurred while getting vendor list"}
    
    conn.close()

    responseJSON = transform_json(responseJSON)

    return {
        "headers": {
            "Content-Type": "application/json",
        },
        "statusCode": 200,
        "body": responseJSON
    }

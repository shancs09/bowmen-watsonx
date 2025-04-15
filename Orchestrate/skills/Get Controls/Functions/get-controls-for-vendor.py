import json
import os
import http.client
import urllib.parse

def get_access_token():
    TOKEN_URL = "iam.cloud.ibm.com"
    #TODO
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
    
    for row in input_json.get("rows", []):  # Handle missing "rows" key
        row_dict = {}
        # first name occurrance is control and second one is test.. Check flag to check if it is first name or second name
        name_field = "control"
        for field in row.get("fields", []):  # Handle missing "fields" key
            if field["name"] == "Name":
                row_dict[name_field] = field["value"]
                name_field = "test_plan"
            elif field["name"] == "OPSS-Test:Test Procedure":
                row_dict["test_procedure"] = field["value"]
            elif field["name"] == "Resource ID":
                row_dict["resource_id"] = field["value"]
        
        if row_dict:
            transformed_data["body"]["hwtable"].append(row_dict)
    
    return transformed_data

def main(params):
    vendor = params.get("vendor", "Microsoft")  # Fix the function call
    token = get_access_token()
    
    if not token:
        return {"statusCode": 500, "body": {"Error": "Failed to get access token"}}

    host = "a67919ef-db35-4266-acc2-0d47bfe4aa06.eu-central-1.aws.openpages.ibm.com"
    endpoint = "/opgrc/api/v2/query/"


    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    query_payload = json.dumps({
        "statement": f"SELECT [SOXControl].[Resource ID], [SOXControl].[Name], [SOXTest].[Resource ID], [SOXTest].[Name], [SOXTest].[OPSS-Test:Test Procedure] FROM [SOXTest] JOIN [SOXControl] ON CHILD([SOXTest]) JOIN [Vendor] ON CHILD([SOXControl]) WHERE [Vendor].[Name] = '{vendor}'",
        "max_rows": 0,
        "case_insensitive": False,
        "honor_primary": False
    })

    try:
        conn = http.client.HTTPSConnection(host)
        conn.request("POST", endpoint, body=query_payload, headers=headers)
        response = conn.getresponse()

        if response.status in (200, 201):
            responseJSON = json.loads(response.read().decode())
        else:
            responseJSON = {"Error": "Error occurred while getting vendor list"}

    except Exception as e:
        responseJSON = {"Error": f"Exception occurred: {e}"}
    
    finally:
        conn.close()
    #print(responseJSON)
    responseJSON = transform_json(responseJSON)

    return {
        "headers": {"Content-Type": "application/json"},
        "statusCode": 200,
        "body": responseJSON
    }

if __name__ == "__main__":
    test_params = {"vendor": "Microsoft"}
    result = main(test_params)
    print(json.dumps(result, indent=2))
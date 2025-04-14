from flask import Flask, request, jsonify
import os
import json
import requests
import threading
import logging

app = Flask(__name__)

TARGET_API_HOST = "https://a67919ef-db35-4266-acc2-0d47bfe4aa06.eu-central-1.aws.openpages.ibm.com"
TARGET_API_PATH = "/opgrc/api/v2/contents"
IAM_URL = "https://iam.cloud.ibm.com/identity/token"

logging.basicConfig(level=logging.DEBUG)

result_map = {
    "Determined": "Pass",
    "Not Determined": "Fail"
}

def get_access_token():
    api_key = os.getenv("API_KEY")
    if not api_key:
        return None

    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
        "apikey": api_key
    }

    response = requests.post(IAM_URL, headers=headers, data=data, verify=False)
    if response.status_code == 200:
        return response.json().get("access_token")
    return None

def generate_update_data(item):
    test_result_input = item.get("test_result", "")
    mapped_value = result_map.get(test_result_input)
    if not mapped_value:
        return None

    return {
        "fields": [
            {
                "name": "OPSS-Shared-Test:Test Result",
                "value": {"name": mapped_value}
            },
            {
                "name": "OPSS-Shared-Test:Testing Status",
                "value": {"name": "Tested"}
            }
        ],
        "type_definition_id": "SOXTestResult",
        "primaryParentId": item.get("resource_id", ""),
        "name": f"TR-{item.get('test_plan', '')}",
        "description": f"Test Result again for Test Plan TR-{item.get('test_plan', '')}"
    }

def post_json_to_target(payload, token):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    response = requests.post(
        TARGET_API_HOST + TARGET_API_PATH,
        headers=headers,
        json=payload,
        verify=False
    )

    if response.ok:
        return True, response.text
    return False, f"{response.status_code} {response.reason} - {response.text}"

def async_update_worker(test_results, callback_url):
    try:
        token = get_access_token()
        if not token:
            raise Exception("Failed to obtain access token")

        success_list = []
        failure_list = []

        for item in test_results:
            test_plan = item.get("test_plan", "UNKNOWN_PLAN")
            op_data = generate_update_data(item)

            if not op_data:
                failure_list.append(test_plan)
                continue

            ok, _ = post_json_to_target(op_data, token)
            if ok:
                success_list.append(test_plan)
            else:
                failure_list.append(test_plan)

        string_response = {
            "output": {
                "update_result": json.dumps({
                    "Passed Controls": success_list,
                    "Failed Controls": failure_list
                })
            }
        }


        headers = {"Content-Type": "application/json"}
        requests.post(callback_url, json=string_response, headers=headers)
        logging.info("[Async] Callback sent successfully")

    except Exception as e:
        logging.error(f"[Async Error] {str(e)}")
        error_payload = {"error": str(e)}
        try:
            requests.post(callback_url, json=error_payload, headers={"Content-Type": "application/json"})
        except:
            logging.error("[Async Error] Failed to notify callback URL")

@app.route("/update", methods=["POST"])
def update_test_results():
    if request.content_type != "application/json":
        return jsonify({"error": "Content-Type must be application/json"}), 400

    callback_url = request.headers.get("callbackUrl")
    if not callback_url:
        return jsonify({"error": "Missing 'callbackUrl' header"}), 422

    try:
        data = request.get_json()
        test_results = data.get("test_results", [])

        if not test_results or not isinstance(test_results, list):
            return jsonify({"error": "Invalid or missing 'test_results' in request payload"}), 400

        thread = threading.Thread(
            target=async_update_worker,
            args=(test_results, callback_url)
        )
        thread.start()

        return jsonify({"message": "Accepted. Processing asynchronously."}), 202

    except Exception as e:
        return jsonify({"error": f"Error processing input: {str(e)}"}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))

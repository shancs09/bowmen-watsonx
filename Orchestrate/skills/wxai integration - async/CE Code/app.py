from flask import Flask, request, jsonify
import json
import os
import requests
import base64
from io import BytesIO
import logging
import time
import threading

logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.debug = True

WXAI_API_ENDPOINT = os.getenv("WXAI_API_ENDPOINT")


def transform_data(wxaiResponseData):
    transformed = {
        "body": {
            "hwtable": []
        }
    }

    for control in wxaiResponseData["controls_data"]:
        transformed_item = {
            "test_control": control["test_control"],
            "test_plan": control["test_plan"],
            "resource_id": control["resource_id"],
            "description": control["description"],
            "test_result": control["llm_answer"]["Compliance_Status"],
            "confidence_score": f"{control['llm_answer']['confidence_score']}",
            "source": control["llm_answer"]["source"],
            "explanation": control["llm_answer"]["explanation"],
            "gap_analysis": control["llm_answer"]["gap_analysis"],
        }

        if control.get("relevant_passages"):
            transformed_item["passage_reference"] = control["relevant_passages"][0]["text"]
        else:
            transformed_item["passage_reference"] = ""

        transformed["body"]["hwtable"].append(transformed_item)

    return transformed


def async_worker(file_entries, controls_input, callback_url):
    try:
        description_input = {
            "description_input": json.dumps(controls_input)
        }

        uploaded_files = []
        for idx, file_info in enumerate(file_entries, start=1):
            filename = file_info.get("filename", f"filename_{idx}")
            content_type = file_info.get("content_type", "application/pdf")
            content_b64 = file_info.get("content")

            file_data = base64.b64decode(content_b64)
            file_stream = BytesIO(file_data)
            uploaded_files.append(("files", (filename, file_stream, content_type)))

        start_time = time.time()
        logging.debug(f"[Async] Start time: {time.ctime(start_time)}")

        api_response = requests.post(
            WXAI_API_ENDPOINT,
            files=uploaded_files,
            data=description_input
        )
        api_response.raise_for_status()

        end_time = time.time()
        logging.debug(f"[Async] End time: {time.ctime(end_time)}")

        logging.debug(f"Total time taken: {end_time - start_time}")

        transformed_data = transform_data(api_response.json())

        string_response = {
            "output": {
                "string1": json.dumps(transformed_data)
            }
        }

        headers = {"Content-Type": "application/json"}
        print(f"Async response: {string_response}")
        response = requests.post(callback_url, json=string_response, headers=headers)
        logging.info(f"[Async] Callback response status: {response.status_code}")

    except Exception as e:
        logging.error(f"[Async Error] {str(e)}")
        error_payload = {"error": str(e)}
        try:
            requests.post(callback_url, json=error_payload, headers={"Content-Type": "application/json"})
        except:
            logging.error("[Async Error] Failed to notify callback URL")


@app.route("/upload", methods=["POST"])
def upload():
    if request.content_type != "application/json":
        return jsonify({"error": f"Content-Type must be application/json"}), 400

    callback_url = request.headers.get("callbackUrl")
    if not callback_url:
        return jsonify({"error": "Missing 'callbackUrl' header"}), 422

    try:
        data = request.get_json()
        controls_input = {"controls_data": data["controls_data"]}
        file_entries = data.get("files", [])

        if not file_entries:
            return jsonify({"error": "No files found in JSON payload"}), 400

        # Kick off async thread
        thread = threading.Thread(
            target=async_worker,
            args=(file_entries, controls_input, callback_url)
        )
        thread.start()

        return jsonify({"message": "Accepted. Processing asynchronously."}), 202

    except Exception as e:
        return jsonify({"error": f"Error processing input: {str(e)}"}), 400


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)
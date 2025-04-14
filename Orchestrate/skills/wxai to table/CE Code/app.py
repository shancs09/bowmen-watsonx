from flask import Flask, request, jsonify
import json

app = Flask(__name__)

def extract_hwtable(data):
    # data is the input dictionary
    output_str = data.get("output", "{}")  # safely get the string
    output_json = json.loads(output_str)   # convert string to dict
    return output_json  # return the extracted dict

@app.route('/process', methods=['POST'])
def process_string():
    data = request.get_json()

    response = extract_hwtable(data)
    print(f"output_json: {response}", flush=True)
    
    return response, 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
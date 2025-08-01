import os
import requests
from flask import Flask, request, jsonify
import os, requests

app = Flask(__name__)

@app.route("/ask", methods=["POST"])
def ask():
    user_question = request.json.get("question")
    if not user_question:
        return jsonify({"error": "Missing question"}), 400

    return jsonify({"llm_response": f"You asked: {user_question}"})

    # Call Databricks LLM
    response = call_llm(user_question)
    return jsonify({"llm_response": response})

def call_llm(prompt):
    url = f"{WORKSPACE_URL}/serving-endpoints/{SERVING_ENDPOINT}/invocations"
    headers = {
        "Authorization": f"Bearer {DATABRICKS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = { "inputs": prompt }

    try:
        r = requests.post(url, headers=headers, json=payload)
        r.raise_for_status()
        return r.json().get("predictions", ["No response"])[0]
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":
    app.run(debug=True)

import os
import openai
import requests
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

load_dotenv()

# Azure OpenAI setup
openai.api_type = "azure"
openai.api_key = os.getenv("AZURE_OPENAI_API_KEY")
openai.api_base = os.getenv("AZURE_OPENAI_ENDPOINT")
openai.api_version = "2023-05-15"
deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT")

# Databricks setup
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN")
DATABRICKS_WAREHOUSE_ID = os.getenv("DATABRICKS_WAREHOUSE_ID")
DATABRICKS_HOST = os.getenv("DATABRICKS_SERVER_HOST")

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json(force=True)
    question = data.get("message")
    if not question:
        return jsonify({"reply": "Missing 'message' in request."})

    try:
        # STEP 1: Use GPT to convert question to SQL
        sql_prompt = f"Convert this user question to Databricks SQL:\n\n{question}"
        sql_response = openai.ChatCompletion.create(
            engine=deployment_name,
            messages=[
                {"role": "system", "content": "You write SQL for Databricks tables using SELECT only."},
                {"role": "user", "content": sql_prompt}
            ],
            temperature=0,
            max_tokens=300
        )
        sql_query = sql_response['choices'][0]['message']['content'].strip("` ")

    except Exception as e:
        return jsonify({"reply": f"Failed to generate SQL:\n\n{str(e)}"})

    try:
        # STEP 2: Execute SQL on Databricks
        headers = {
            "Authorization": f"Bearer {DATABRICKS_TOKEN}",
            "Content-Type": "application/json"
        }
        payload = {
            "statement": sql_query,
            "warehouse_id": DATABRICKS_WAREHOUSE_ID
        }

        sql_result = requests.post(
            f"{DATABRICKS_HOST}/api/2.0/sql/statements",
            headers=headers,
            json=payload
        ).json()

        if "error" in sql_result:
            return jsonify({"reply": f"Databricks error:\n\n{sql_result['error']['message']}"})

        # STEP 3: Summarize with GPT
        summary_prompt = f"User question: {question}\n\nSQL: {sql_query}\n\nRaw result:\n{sql_result}\n\nSummarize this for a business user."
        final_response = openai.ChatCompletion.create(
            engine=deployment_name,
            messages=[
                {"role": "system", "content": "You summarize SQL results into clear business answers."},
                {"role": "user", "content": summary_prompt}
            ],
            temperature=0.5,
            max_tokens=250
        )
        reply = final_response['choices'][0]['message']['content'].strip()
        return jsonify({"reply": reply})

    except Exception as e:
        return jsonify({"reply": f"Error querying Databricks:\n\n{str(e)}"})

if __name__ == "__main__":
    app.run(debug=True, port=8000)

import requests
import uuid

url = "http://localhost:8000/api/topology/query"
payload = {
    "query": "Show me the path from Dallas to Austin",
    "ui_context": {},
    "session_id": str(uuid.uuid4())
}

try:
    response = requests.post(url, json=payload)
    print(f"Status Code: {response.status_code}")
    print(f"Response Body: {response.text}")
except Exception as e:
    print(f"Error: {e}")

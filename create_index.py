import json
import boto3
import requests
from requests_aws4auth import AWS4Auth

# Replace with your values
OPENSEARCH_ENDPOINT = "https://cloudops-chatbot-kb-xxxxxxxx.us-west-2.aoss.amazonaws.com"
INDEX_NAME = "confluence-pages"
REGION = "us-west-2"

session = boto3.Session()
credentials = session.get_credentials()
awsauth = AWS4Auth(
    credentials.access_key,
    credentials.secret_key,
    credentials.token,
    REGION,
    "aoss"
)

url = f"{OPENSEARCH_ENDPOINT}/{INDEX_NAME}"
headers = { "Content-Type": "application/json" }

body = {
    "settings": {
        "index": {
            "knn": True
        }
    },
    "mappings": {
        "properties": {
            "title":    { "type": "text" },
            "content":  { "type": "text" },
            "embedding": {
                "type": "knn_vector",
                "dimension": 1536,
                "method": {
                    "name": "hnsw",
                    "engine": "faiss",
                    "space_type": "innerproduct"
                }
            }
        }
    }
}

response = requests.put(url, auth=awsauth, headers=headers, data=json.dumps(body))
print("Status Code:", response.status_code)
print("Response:", response.text)

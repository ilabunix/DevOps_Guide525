import json
import boto3
import os
import requests
from requests.auth import HTTPBasicAuth
from config import OPENSEARCH_ENDPOINT, OPENSEARCH_INDEX, OS_USERNAME, OS_PASSWORD

bedrock = boto3.client("bedrock-runtime")

def get_titan_embedding(text):
    payload = { "inputText": text }
    response = bedrock.invoke_model(
        modelId="amazon.titan-embed-text-v2:0",
        contentType="application/json",
        accept="application/json",
        body=json.dumps(payload)
    )
    response_body = json.loads(response['body'].read())
    embedding = response_body['embedding']

    # Ensure correct vector length
    if len(embedding) < 1536:
        embedding += [0.0] * (1536 - len(embedding))
    elif len(embedding) > 1536:
        embedding = embedding[:1536]

    return [float(x) for x in embedding]

def lambda_handler(event, context):
    query_text = event.get("query", "")
    if not query_text:
        return { "statusCode": 400, "body": "Missing query input." }

    vector = get_titan_embedding(query_text)

    search_payload = {
        "size": 3,
        "query": {
            "knn": {
                "embedding": {
                    "vector": vector,
                    "k": 3
                }
            }
        }
    }

    url = f"{OPENSEARCH_ENDPOINT}/{OPENSEARCH_INDEX}/_search"
    auth = HTTPBasicAuth(OS_USERNAME, OS_PASSWORD)
    headers = { "Content-Type": "application/json" }

    response = requests.post(url, headers=headers, auth=auth, data=json.dumps(search_payload))

    if response.status_code not in [200]:
        return {
            "statusCode": response.status_code,
            "body": f"Error from OpenSearch: {response.text}"
        }

    hits = response.json().get("hits", {}).get("hits", [])
    results = [
        {
            "title": hit["_source"]["title"],
            "content": hit["_source"]["content"],
            "score": hit["_score"]
        }
        for hit in hits
    ]

    return {
        "statusCode": 200,
        "body": json.dumps(results, indent=2)
    }
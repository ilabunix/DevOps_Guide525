def lambda_handler(event, context):
    query_text = event.get("query", "")
    if not query_text:
        return { "statusCode": 400, "body": "Missing query input." }

    vector = get_titan_embedding(query_text)

    # Perform KNN vector search in OpenSearch
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

    if response.status_code not in [200, 201]:
        return {
            "statusCode": response.status_code,
            "body": f"Error from OpenSearch: {response.text}"
        }

    hits = response.json().get("hits", {}).get("hits", [])
    retrieved_chunks = [ hit["_source"]["content"] for hit in hits ]

    # 🧠 Combine retrieved chunks for Claude input
    context_text = "\n\n".join(retrieved_chunks)

    prompt = f"""
You are a helpful assistant. Answer the following user question based on the provided context.

Context:
{context_text}

Question:
{query_text}

Answer:
"""

    # 🧠 Call Claude using Bedrock
    bedrock = boto3.client("bedrock-runtime")
    bedrock_response = bedrock.invoke_model(
        modelId="anthropic.claude-3-sonnet-20240229",
        contentType="application/json",
        accept="application/json",
        body=json.dumps({
            "messages": [
                { "role": "user", "content": prompt }
            ],
            "max_tokens": 500
        })
    )

    answer_body = json.loads(bedrock_response['body'].read())
    final_answer = answer_body.get("content", "No answer generated.")

    return {
        "statusCode": 200,
        "body": json.dumps({
            "answer": final_answer,
            "matches": retrieved_chunks
        }, indent=2)
    }
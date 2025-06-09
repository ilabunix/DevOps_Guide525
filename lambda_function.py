import json
import uuid
from config import *
from atlassian import Confluence
import requests

def lambda_handler(event, context):
    confluence = Confluence(
        url=CONFLUENCE_URL,
        username=CONFLUENCE_EMAIL,
        password=CONFLUENCE_API_TOKEN
    )

    pages = confluence.get_all_pages_from_space(CONFLUENCE_SPACE_KEY, limit=10)
    docs = []

    for page in pages:
        content = confluence.get_page_by_id(page['id'], expand='body.storage')
        title = content['title']
        html = content['body']['storage']['value']
        text = strip_html_tags(html)
        chunks = split_text(text, chunk_size=512)

        for chunk in chunks:
            doc_id = str(uuid.uuid4())
            doc = {
                "id": doc_id,
                "title": title,
                "content": chunk
            }
            index_document(doc)

    return {
        "statusCode": 200,
        "body": json.dumps(f"Indexed {len(pages)} pages.")
    }

def strip_html_tags(html):
    from bs4 import BeautifulSoup
    return BeautifulSoup(html, "html.parser").get_text()

def split_text(text, chunk_size=512):
    words = text.split()
    return [" ".join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]

def index_document(doc):
    headers = {"Content-Type": "application/json"}
    res = requests.put(
        f"{OPENSEARCH_ENDPOINT}/{OPENSEARCH_INDEX}/_doc/{doc['id']}",
        headers=headers,
        data=json.dumps(doc),
        auth=(AWS4AuthViaIAM())  # Optional: can inject AWS IAM auth signer if OpenSearch needs it
    )
    if res.status_code not in [200, 201]:
        print("Failed to index:", res.text)

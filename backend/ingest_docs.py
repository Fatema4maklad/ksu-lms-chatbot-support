import os
import glob
import uuid
import requests
from dotenv import load_dotenv

# Load API key
load_dotenv(dotenv_path="../.env")
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env")

# REST Endpoints
CHROMA_BASE = "http://localhost:8001/api/v2/tenants/default_tenant/databases/default_database/collections"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:embedContent?key={API_KEY}"

DOCS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "blackboard_docs"))

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50):
    words = text.split()
    chunks = []
    step = max(1, chunk_size - overlap)
    for i in range(0, len(words), step):
        chunk = " ".join(words[i : i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
    return chunks

# 1. Ensure Collection Exists
res = requests.post(CHROMA_BASE, json={"name": "ksu_lms_docs"})
if res.status_code in [200, 201]:
    collection_id = res.json()["id"]
elif res.status_code == 409 or "UniqueConstraintError" in res.text:
    res = requests.get(f"{CHROMA_BASE}/ksu_lms_docs")
    collection_id = res.json()["id"]
else:
    raise RuntimeError(f"Chroma connection failed: {res.text}")

# 2. Load Documents (Recursive Search)
txt_pattern = os.path.join(DOCS_DIR, "**", "*.txt")
md_pattern = os.path.join(DOCS_DIR, "**", "*.md")

file_paths = glob.glob(txt_pattern, recursive=True) + glob.glob(md_pattern, recursive=True)

if not file_paths:
    print(f"⚠️ No .txt or .md files found in {DOCS_DIR} or its subfolders")
    exit()

print(f"📂 Found {len(file_paths)} document(s) in blackboard_docs/")

# 3. Process & Ingest
all_ids, all_embeddings, all_docs, all_metas = [], [], [], []

for file_path in file_paths:
    filename = os.path.basename(file_path)
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    chunks = chunk_text(content, chunk_size=500, overlap=50)
    print(f"📄 Processing '{filename}' -> {len(chunks)} chunks")

    for i, chunk in enumerate(chunks):
        res = requests.post(GEMINI_URL, json={
            "model": "models/gemini-embedding-001",
            "content": {"parts": [{"text": chunk}]},
            "taskType": "RETRIEVAL_DOCUMENT"
        })

        if res.status_code == 200:
            vector = res.json()["embedding"]["values"]
            all_ids.append(str(uuid.uuid4()))
            all_embeddings.append(vector)
            all_docs.append(chunk)
            all_metas.append({"source": filename, "chunk_index": i})
        else:
            print(f"⚠️ Embedding failed for {filename} [chunk {i}]: {res.text}")

# 4. Push to ChromaDB in batches
if all_ids:
    print(f"💾 Ingesting {len(all_ids)} total chunks into ChromaDB...")
    add_res = requests.post(f"{CHROMA_BASE}/{collection_id}/add", json={
        "ids": all_ids,
        "embeddings": all_embeddings,
        "documents": all_docs,
        "metadatas": all_metas
    })

    if add_res.status_code in [200, 201]:
        print("✅ Ingestion complete! Knowledge base is fully indexed.")
    else:
        print(f"⚠️ Chroma error during add: {add_res.text}")
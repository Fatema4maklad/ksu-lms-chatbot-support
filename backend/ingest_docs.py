import os
import glob
import uuid
import requests

# REST Endpoints
CHROMA_BASE = "http://localhost:8001/api/v2/tenants/default_tenant/databases/default_database/collections"
OLLAMA_BASE = "http://localhost:11434/api"
OLLAMA_EMBED_MODEL = "nomic-embed-text"
DOCS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "blackboard_docs"))


def embed_text_ollama(text: str):
    res = requests.post(f"{OLLAMA_BASE}/embeddings", json={
        "model": OLLAMA_EMBED_MODEL,
        "prompt": text
    })
    if res.status_code == 200:
        return res.json()["embedding"]
    raise RuntimeError(f"Failed to embed: {res.text}")


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50):
    words = text.split()
    chunks = []
    step = max(1, chunk_size - overlap)
    for i in range(0, len(words), step):
        chunk = " ".join(words[i : i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
    return chunks


# WRAPPED: all logic below moved inside this function so the file can be
# safely imported by routers/admin.py without running on import. Behavior
# is unchanged from the original script.
def run_ingestion():
    log = []

    # 1. Reset Collection (Wipe old Gemini vectors and create fresh Ollama ones)
    try:
        # Delete the old collection if it exists
        requests.delete(f"{CHROMA_BASE}/ksu_lms_docs")
        log.append("🗑️ Deleted old Gemini vector collection.")
    except Exception:
        pass

    # Create fresh collection
    res = requests.post(CHROMA_BASE, json={"name": "ksu_lms_docs"})
    if res.status_code in [200, 201]:
        collection_id = res.json()["id"]
        log.append("✨ Created new Ollama vector collection.")
    else:
        raise RuntimeError(f"Chroma connection failed: {res.text}")

    # 2. Load Documents (Recursive Search)
    txt_pattern = os.path.join(DOCS_DIR, "**", "*.txt")
    md_pattern = os.path.join(DOCS_DIR, "**", "*.md")

    file_paths = glob.glob(txt_pattern, recursive=True) + glob.glob(md_pattern, recursive=True)

    if not file_paths:
        log.append(f"⚠️ No .txt or .md files found in {DOCS_DIR} or its subfolders")
        return {"status": "no_files", "log": log}

    log.append(f"📂 Found {len(file_paths)} document(s) in blackboard_docs/")

    # 3. Process & Ingest
    all_ids, all_embeddings, all_docs, all_metas = [], [], [], []

    for file_path in file_paths:
        filename = os.path.basename(file_path)
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        chunks = chunk_text(content, chunk_size=500, overlap=50)
        log.append(f"📄 Processing '{filename}' -> {len(chunks)} chunks")

        for i, chunk in enumerate(chunks):
            try:
                # Call the local Ollama function instead of the Gemini API
                vector = embed_text_ollama(chunk)
                all_ids.append(str(uuid.uuid4()))
                all_embeddings.append(vector)
                all_docs.append(chunk)
                all_metas.append({"source": filename, "chunk_index": i})
            except Exception as e:
                log.append(f"⚠️ Embedding failed for {filename} [chunk {i}]: {str(e)}")

    # 4. Push to ChromaDB in batches
    if all_ids:
        log.append(f"💾 Ingesting {len(all_ids)} total chunks into ChromaDB...")
        add_res = requests.post(f"{CHROMA_BASE}/{collection_id}/add", json={
            "ids": all_ids,
            "embeddings": all_embeddings,
            "documents": all_docs,
            "metadatas": all_metas
        })

        if add_res.status_code in [200, 201]:
            log.append("✅ Ingestion complete! Knowledge base is fully indexed.")
            return {"status": "success", "chunks_embedded": len(all_ids), "log": log}
        else:
            log.append(f"⚠️ Chroma error during add: {add_res.text}")
            return {"status": "error", "log": log}

    return {"status": "no_chunks", "log": log}


if __name__ == "__main__":
    result = run_ingestion()
    for line in result["log"]:
        print(line)
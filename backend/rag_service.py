import os
import requests
import time
from dotenv import load_dotenv

load_dotenv(dotenv_path="../.env")
API_KEY = os.getenv("GEMINI_API_KEY")

CHROMA_BASE = "http://localhost:8001/api/v2/tenants/default_tenant/databases/default_database/collections"
EMBED_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-001:embedContent?key={API_KEY}"
GEN_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key={API_KEY}"

def get_collection_id(name="ksu_lms_docs"):
    res = requests.get(f"{CHROMA_BASE}/{name}")
    if res.status_code == 200:
        return res.json().get("id")
    return None

def embed_query(query: str):
    """Embeds user question using RETRIEVAL_QUERY task type."""
    res = requests.post(EMBED_URL, json={
        "model": "models/gemini-embedding-001",
        "content": {"parts": [{"text": query}]},
        "taskType": "RETRIEVAL_QUERY"
    }, timeout=10) # <-- Added timeout here
    
    if res.status_code == 200:
        return res.json()["embedding"]["values"]
    raise RuntimeError(f"Embedding failed: {res.text}")

def search_chunks(query_vector: list, n_results: int = 3):
    """Queries ChromaDB REST API for nearest neighbors."""
    collection_id = get_collection_id()
    if not collection_id:
        return []
    
    query_url = f"{CHROMA_BASE}/{collection_id}/query"
    payload = {
        "query_embeddings": [query_vector],
        "n_results": n_results
    }
    res = requests.post(query_url, json=payload)
    if res.status_code == 200:
        data = res.json()
        documents = data.get("documents", [[]])[0]
        return documents
    return []

def ask_lms_assistant(question: str):
    q_vector = embed_query(question)
    chunks = search_chunks(q_vector, n_results=2)
    context_text = "\n---\n".join(chunks)

    system_prompt = (
        "You are the official technical support assistant for the Blackboard Learning Management System at King Saud University. "
        "Answer the user's question accurately using ONLY the information provided in the Context below.\n\n"
        "STRICT RULES:\n"
        "1. Language Matching: Auto-detect the language of the user's question. If the question is in Arabic, reply in Arabic. If it is in English, reply in English.\n"
        "2. Natural Persona: NEVER use phrases like 'based on the documents', 'according to the files', or mention the 'context'. Present the information directly as an expert who already knows the answer.\n\n"
        f"Context:\n{context_text}\n\n"
        f"Question: {question}"
    )

    payload = {
        "contents": [{"parts": [{"text": system_prompt}]}],
        "generationConfig": {"temperature": 0.2}
    }
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # <-- Added timeout=10 here to prevent the infinite hang
            res = requests.post(GEN_URL, json=payload, timeout=40)
            
            if res.status_code == 200:
                return res.json()["candidates"][0]["content"]["parts"][0]["text"]
                
            elif res.status_code == 503:
                print(f"⚠️ Free tier busy. Retrying in {2 ** attempt} seconds...")
                time.sleep(2 ** attempt)
                continue
                
            return f"Error: {res.text}"
            
        except requests.exceptions.Timeout:
            print(f"⚠️ Request timed out. Retrying in {2 ** attempt} seconds...")
            time.sleep(2 ** attempt)
            continue
            
    return "عذراً، النظام يواجه ضغطاً عالياً حالياً. يرجى المحاولة مرة أخرى بعد قليل."
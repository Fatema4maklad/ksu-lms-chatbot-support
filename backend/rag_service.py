import os
import requests
import time
from dotenv import load_dotenv

load_dotenv(dotenv_path="../.env")

# Ollama local endpoints
OLLAMA_BASE = "http://localhost:11434/api"
OLLAMA_LLM_MODEL = "qwen2.5" # Replace with your chosen model (e.g., mistral, aya)
OLLAMA_EMBED_MODEL = "nomic-embed-text" # Recommended for embeddings

CHROMA_BASE = "http://localhost:8001/api/v2/tenants/default_tenant/databases/default_database/collections"

def get_collection_id(name="ksu_lms_docs"):
    res = requests.get(f"{CHROMA_BASE}/{name}")
    if res.status_code == 200:
        return res.json().get("id")
    return None

def embed_query(query: str):
    """Embeds user question using Ollama."""
    try:
        res = requests.post(f"{OLLAMA_BASE}/embeddings", json={
            "model": OLLAMA_EMBED_MODEL,
            "prompt": query
        }, timeout=15)
        
        if res.status_code == 200:
            return res.json()["embedding"]
        raise RuntimeError(f"Embedding failed: {res.text}")
    except requests.exceptions.ConnectionError:
        raise RuntimeError("Failed to connect to Ollama. Ensure the server is running.")

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
    try:
        q_vector = embed_query(question)
    except Exception as e:
        return f"خطأ في الاتصال بالخادم المحلي: {str(e)}"

    chunks = search_chunks(q_vector, n_results=2)
    context_text = "\n---\n".join(chunks)

    system_prompt = f"""You are the official KSU Blackboard Technical Support Assistant. 
You are highly professional and MUST follow these rules exactly:

<rules>
1. LANGUAGE: Always reply in the exact same language as the <user_query>. If Arabic, reply in perfect, natural Arabic. 
2. NO CHINESE: Under NO circumstances should you output Chinese characters or any language other than Arabic and English.
3. CHITCHAT: If the <user_query> is a greeting, small talk, or an insult, IGNORE the <context>. Reply politely asking how you can help.
4. PRIMARY RAG: Try to answer the user's question using the information in the <context>.
5. SMART FALLBACK: If the <context> does not contain the answer, DO NOT say you don't know. Instead, use your general expert knowledge about Blackboard LMS to provide a helpful, step-by-step troubleshooting answer.
</rules>

<context>
{context_text}
</context>

<user_query>
{question}
</user_query>
"""

    payload = {
        "model": OLLAMA_LLM_MODEL,
        "prompt": system_prompt,
        "stream": False,
        "options": {
            "temperature": 0.2
        }
    }
    
    try:
        # Give local inference more time depending on server hardware
        res = requests.post(f"{OLLAMA_BASE}/generate", json=payload, timeout=60)
        
        if res.status_code == 200:
            return res.json()["response"]
            
        return f"Error: {res.text}"
        
    except requests.exceptions.Timeout:
        return "عذراً، النظام يأخذ وقتاً طويلاً للرد. يرجى المحاولة مرة أخرى."
    except requests.exceptions.ConnectionError:
        return "عذراً، لا يمكن الاتصال بمزود الذكاء الاصطناعي المحلي. يرجى التأكد من تشغيل الخادم."
import os
import re
import requests
import time
from dotenv import load_dotenv

load_dotenv(dotenv_path="../.env")

# Ollama local endpoints
OLLAMA_BASE = "http://localhost:11434/api"
OLLAMA_LLM_MODEL = "qwen2.5" # Replace with your chosen model (e.g., mistral, aya)
OLLAMA_EMBED_MODEL = "nomic-embed-text" # Recommended for embeddings

CHROMA_BASE = "http://localhost:8001/api/v2/tenants/default_tenant/databases/default_database/collections"

# How many prior turns (user+assistant messages) to fold into the prompt.
# Kept modest since qwen2.5's context window and local inference speed both
# degrade the more history is stuffed into every request.
MAX_HISTORY_TURNS = 6

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
        }, timeout=60)
        
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


# CJK Unified Ideographs (and related supplementary blocks) — matches
# Chinese characters that qwen2.5 occasionally leaks despite the explicit
# "NO CHINESE" rule in the prompt below. Prompting alone doesn't catch this
# 100% of the time, so this is a backend safety net, not a replacement for
# the rule.
_CJK_PATTERN = re.compile(r'[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]+')


def strip_chinese(text: str) -> str:
    cleaned = _CJK_PATTERN.sub('', text)
    # Clean up whitespace/punctuation left behind by the removal
    cleaned = re.sub(r'[ \t]{2,}', ' ', cleaned)
    cleaned = re.sub(r'[?？]{2,}', '?', cleaned)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    return cleaned.strip()


def build_history_block(history: list) -> str:
    """
    Renders prior turns as a simple transcript. `history` is a list of
    {"role": "user"|"assistant", "content": str} dicts in chronological
    order (oldest first) and does NOT include the current question.
    """
    if not history:
        return "(no prior messages in this conversation)"

    recent = history[-(MAX_HISTORY_TURNS * 2):]
    lines = []
    for msg in recent:
        label = "User" if msg.get("role") == "user" else "Assistant"
        lines.append(f"{label}: {msg.get('content', '')}")
    return "\n".join(lines)


def ask_lms_assistant(question: str, history: list = None):
    try:
        q_vector = embed_query(question)
    except Exception as e:
        return f"خطأ في الاتصال بالخادم المحلي: {str(e)}"

    chunks = search_chunks(q_vector, n_results=2)
    context_text = "\n---\n".join(chunks)
    history_text = build_history_block(history or [])

    system_prompt = f"""You are the official KSU Blackboard Technical Support Assistant. 
You are highly professional and MUST follow these rules exactly:

<rules>
1. LANGUAGE: Always reply in the exact same language as the <user_query>. If Arabic, reply in perfect, natural Arabic. 
2. NO CHINESE: Under NO circumstances should you output Chinese characters or any language other than Arabic and English.
3. CHITCHAT: If the <user_query> is a greeting, small talk, or an insult, IGNORE the <context>. Reply politely asking how you can help.
4. PRIMARY RAG: Try to answer the user's question using the information in the <context>.
5. SMART FALLBACK: If the <context> does not contain the answer, DO NOT say you don't know. Instead, use your general expert knowledge about Blackboard LMS to provide a helpful, step-by-step troubleshooting answer.
6. MEMORY: Use <conversation_history> to understand references to earlier messages (e.g. "it", "that error", "the same problem"). Do not repeat information you already gave unless asked to.
</rules>

<conversation_history>
{history_text}
</conversation_history>

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
        # Give local inference more time depending on server hardware — the
        # first request after Ollama starts is slow because it has to load
        # the model into memory; a 2-minute ceiling covers that cold start.
        res = requests.post(f"{OLLAMA_BASE}/generate", json=payload, timeout=120)
        
        if res.status_code == 200:
            return strip_chinese(res.json()["response"])
            
        return f"Error: {res.text}"
        
    except requests.exceptions.Timeout:
        return "عذراً، النظام يأخذ وقتاً طويلاً للرد. يرجى المحاولة مرة أخرى."
    except requests.exceptions.ConnectionError:
        return "عذراً، لا يمكن الاتصال بمزود الذكاء الاصطناعي المحلي. يرجى التأكد من تشغيل الخادم."
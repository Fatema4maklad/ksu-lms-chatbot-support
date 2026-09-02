import os
import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path="../.env")
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    print("⚠️ Error: GEMINI_API_KEY not found in .env file")
    exit()

# Updated to the current active embedding model
MODEL = "gemini-embedding-001"
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:embedContent?key={API_KEY}"

sample_text = "كيف يمكنني الدخول إلى نظام البلاك بورد؟"

payload = {
    "model": f"models/{MODEL}",
    "content": {
        "parts": [{
            "text": sample_text
        }]
    },
    "taskType": "RETRIEVAL_DOCUMENT"
}

response = requests.post(URL, json=payload)

if response.status_code == 200:
    embedding = response.json()['embedding']['values']
    print("✅ Gemini API Connected via REST!")
    print(f"📝 Original Text: {sample_text}")
    print(f"📏 Vector Size: {len(embedding)} dimensions")
    print(f"🔢 First 5 numbers: {embedding[:5]}")
else:
    print(f"⚠️ Error: {response.status_code}")
    print(response.text)
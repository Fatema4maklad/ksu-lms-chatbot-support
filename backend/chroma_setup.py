import requests

# The updated v2 endpoint including the default tenant and database
CHROMA_URL = "http://localhost:8001/api/v2/tenants/default_tenant/databases/default_database/collections"

# Attempt to create the collection
response = requests.post(CHROMA_URL, json={
    "name": "ksu_lms_docs",
    "metadata": {"hnsw:space": "cosine"}
})

if response.status_code in [200, 201]:
    data = response.json()
    print(f"✅ ChromaDB Connected via REST! Collection ID: {data['id']}")
elif response.status_code == 409 or "UniqueConstraintError" in response.text:
    print("✅ ChromaDB Connected! Collection 'ksu_lms_docs' already exists.")
else:
    print(f"⚠️ Error: {response.status_code} - {response.text}")
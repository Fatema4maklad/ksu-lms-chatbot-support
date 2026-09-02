def chunk_text(text, chunk_size=500, overlap=50):
    """Splits text into chunks of `chunk_size` words with `overlap` words."""
    words = text.split()
    chunks = []
    
    # Step through the words array, shifting by (chunk_size - overlap)
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i : i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
            
    return chunks

# --- Test the Logic ---
if __name__ == "__main__":
    # Generate dummy Arabic Blackboard data to test the word count
    dummy_text = "كيف يمكنني الدخول إلى نظام البلاك بورد؟ " * 150 
    
    print("⏳ Processing document...")
    resulting_chunks = chunk_text(dummy_text, chunk_size=500, overlap=50)
    
    print(f"✅ Document split into {len(resulting_chunks)} chunks.")
    
    for index, chunk in enumerate(resulting_chunks):
        word_count = len(chunk.split())
        print(f"📦 Chunk {index + 1}: {word_count} words")
        
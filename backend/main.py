import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from rag_service import ask_lms_assistant
from routers import auth

from database import engine, Base, SessionLocal
from models import Agent
from passlib.hash import bcrypt

Base.metadata.create_all(bind=engine)

# Seed the test agent if it doesn't exist
db = SessionLocal()
if not db.query(Agent).filter(Agent.email == "agent@ksu.edu.sa").first():
    test_agent = Agent(
        name="Test Agent", 
        email="agent@ksu.edu.sa", 
        password_hash=bcrypt.hash("test1234")
    )
    db.add(test_agent)
    db.commit()
db.close()

# Add backend directory to path to prevent module import errors
sys.path.append(str(Path(__file__).resolve().parent))

app = FastAPI(title="KSU LMS Support Chatbot API")

# Configure CORS so the React frontend can communicate with FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register auth router (Removed agent_auth, removed prefix to match React)
app.include_router(auth.router)

# This exact variable name "question" prevents the 422 Unprocessable Content error
class ChatRequest(BaseModel):
    question: str

@app.get("/api/test")
def test_endpoint():
    return {"message": "Backend is online and running!"}

@app.post("/api/chat")
def chat_endpoint(request: ChatRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    
    try:
        reply = ask_lms_assistant(request.question)
        return {"answer": reply}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
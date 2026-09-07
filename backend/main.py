import sys
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional

import bcrypt
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from rag_service import ask_lms_assistant
from routers import auth

from database import engine, Base, SessionLocal, get_db
from models import Agent, Conversation, Message, Feedback
from schemas import ChatRequest, ChatResponse, FeedbackRequest, FeedbackResponse
from dependencies import get_optional_current_user

Base.metadata.create_all(bind=engine)

# Seed the test agent if it doesn't exist
db = SessionLocal()
if not db.query(Agent).filter(Agent.email == "agent@ksu.edu.sa").first():
    test_agent = Agent(
        name="Test Agent", 
        email="agent@ksu.edu.sa", 
        password_hash=bcrypt.hashpw("test1234".encode(), bcrypt.gensalt()).decode()
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

# How many prior messages (both roles combined) to pull back out of the DB
# and feed into the LLM prompt as context.
MAX_HISTORY_MESSAGES = 12


@app.get("/api/test")
def test_endpoint():
    return {"message": "Backend is online and running!"}


@app.post("/api/chat", response_model=ChatResponse)
def chat_endpoint(
    request: ChatRequest,
    db: Session = Depends(get_db),
    user_id: Optional[int] = Depends(get_optional_current_user),
):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    # Resolve the conversation this message belongs to, or start a new one.
    conversation = None
    if request.conversation_id:
        conversation = db.query(Conversation).filter(
            Conversation.conversation_uuid == request.conversation_id
        ).first()

    if not conversation:
        conversation = Conversation(
            conversation_uuid=str(uuid.uuid4()),
            user_id=user_id,
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    # Pull recent prior turns (oldest first) to give the LLM conversational memory.
    history_rows = (
        db.query(Message)
        .filter(Message.conversation_id == conversation.id)
        .order_by(Message.id.desc())
        .limit(MAX_HISTORY_MESSAGES)
        .all()
    )
    history_rows.reverse()
    history = [{"role": m.role, "content": m.content} for m in history_rows]

    # Persist the user's message before calling the model, so it survives
    # even if generation fails partway through.
    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=request.question,
    )
    db.add(user_message)
    db.commit()

    try:
        reply = ask_lms_assistant(request.question, history=history)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    assistant_message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=reply,
    )
    db.add(assistant_message)
    db.commit()
    db.refresh(assistant_message)

    return ChatResponse(
        answer=reply,
        conversation_id=conversation.conversation_uuid,
        message_id=assistant_message.id,
    )


@app.post("/api/feedback", response_model=FeedbackResponse)
def feedback_endpoint(request: FeedbackRequest, db: Session = Depends(get_db)):
    if request.rating not in ("up", "down"):
        raise HTTPException(status_code=400, detail="rating must be 'up' or 'down'")

    message = db.query(Message).filter(Message.id == request.message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    existing = db.query(Feedback).filter(Feedback.message_id == request.message_id).first()
    if existing:
        existing.rating = request.rating
    else:
        existing = Feedback(message_id=request.message_id, rating=request.rating)
        db.add(existing)

    db.commit()

    return FeedbackResponse(message_id=request.message_id, rating=request.rating)
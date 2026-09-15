import sys
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional

import bcrypt
from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
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


# -----------------------------------------
# Live agent handoff (WebSocket)
# -----------------------------------------

class ConnectionManager:
    """
    Tracks active WebSocket connections per conversation. Both the user's
    browser tab and an agent's dashboard tab connect to the same
    conversation_id "room" and receive each other's messages live.
    """
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, conversation_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.setdefault(conversation_id, []).append(websocket)

    def disconnect(self, conversation_id: str, websocket: WebSocket):
        if conversation_id in self.active_connections:
            self.active_connections[conversation_id].remove(websocket)
            if not self.active_connections[conversation_id]:
                del self.active_connections[conversation_id]

    async def broadcast(self, conversation_id: str, payload: dict):
        for connection in self.active_connections.get(conversation_id, []):
            await connection.send_json(payload)


manager = ConnectionManager()


def _serialize_message(m: Message) -> dict:
    return {
        "id": m.id,
        "role": m.role,
        "agent_id": m.agent_id,
        "content": m.content,
        "created_at": m.created_at.isoformat(),
    }


@app.websocket("/ws/chat/{conversation_id}")
async def websocket_chat(websocket: WebSocket, conversation_id: str):
    db = SessionLocal()
    try:
        print(f"[WS DEBUG] Looking for conversation_id={conversation_id!r}")
        all_uuids = [c.conversation_uuid for c in db.query(Conversation).all()]
        print(f"[WS DEBUG] UUIDs currently in DB: {all_uuids}")

        conversation = db.query(Conversation).filter(
            Conversation.conversation_uuid == conversation_id
        ).first()
        print(f"[WS DEBUG] Query result: {conversation}")

        if not conversation:
            await websocket.close(code=4004)
            return

        await manager.connect(conversation_id, websocket)

        # Push full history immediately on connect, so a user reconnecting
        # or an agent claiming the chat sees everything that came before.
        history_rows = (
            db.query(Message)
            .filter(Message.conversation_id == conversation.id)
            .order_by(Message.id.asc())
            .all()
        )
        await websocket.send_json({
            "type": "history",
            "messages": [_serialize_message(m) for m in history_rows],
        })

        try:
            while True:
                data = await websocket.receive_json()
                role = data.get("role")
                content = (data.get("content") or "").strip()
                agent_id = data.get("agent_id")

                if role not in ("user", "agent") or not content:
                    continue

                new_message = Message(
                    conversation_id=conversation.id,
                    role=role,
                    agent_id=agent_id if role == "agent" else None,
                    content=content,
                )
                db.add(new_message)
                db.commit()
                db.refresh(new_message)

                await manager.broadcast(conversation_id, {
                    "type": "message",
                    "message": _serialize_message(new_message),
                })
        except WebSocketDisconnect:
            manager.disconnect(conversation_id, websocket)
    finally:
        db.close()


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
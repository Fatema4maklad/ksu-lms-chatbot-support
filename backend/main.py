import sys
import uuid
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List
from collections import Counter

import bcrypt
from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel

from rag_service import ask_lms_assistant, generate_faq_summary
from routers import auth

from database import engine, Base, SessionLocal, get_db
from models import Agent, Conversation, Message, Feedback, User
from schemas import ChatRequest, ChatResponse, FeedbackRequest, FeedbackResponse
from dependencies import get_optional_current_user, get_current_agent

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

# The exact text the frontend sends when a user clicks "أخرى (اكتب مشكلتك)".
ESCALATION_TRIGGER_TEXT = "مشكلة أخرى"

# Consecutive 👎 on assistant replies (within one conversation) needed to
# auto-escalate to a human agent.
CONSECUTIVE_DOWNVOTES_TO_ESCALATE = 2

ESCALATION_REPLY = (
    "تم تحويلك إلى أحد موظفي الدعم الفني، يرجى الانتظار قليلاً حتى ينضم أحدهم للمحادثة.\n\n"
    "You've been connected to a human support agent. Please wait a moment while someone joins the chat."
)


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


# Tracks agent dashboard sockets subscribed to queue updates (distinct from
# both the per-conversation chat sockets above and the per-agent presence
# sockets below). Any agent dashboard connected here gets a live push the
# moment a new conversation escalates, via _notify_escalation.
queue_subscribers: list[WebSocket] = []


def _serialize_message(m: Message) -> dict:
    return {
        "id": m.id,
        "role": m.role,
        "agent_id": m.agent_id,
        "content": m.content,
        "created_at": m.created_at.isoformat(),
    }


def _serialize_conversation_summary(c: Conversation, db: Session) -> dict:
    last_message = (
        db.query(Message)
        .filter(Message.conversation_id == c.id)
        .order_by(Message.id.desc())
        .first()
    )
    # Anonymous conversations (no logged-in student) have no user_id, so
    # there's no name or university ID to attach.
    user = db.query(User).filter(User.id == c.user_id).first() if c.user_id else None
    return {
        "conversation_id": c.conversation_uuid,
        "status": c.status,
        "ticket_status": c.ticket_status,
        "created_at": c.created_at.isoformat(),
        "user_id": c.user_id,
        "university_id": user.university_id if user else None,
        "user_name": user.name if user else None,
        "last_message": last_message.content if last_message else None,
    }


@app.websocket("/ws/chat/{conversation_id}")
async def websocket_chat(websocket: WebSocket, conversation_id: str):
    db = SessionLocal()
    try:
        conversation = db.query(Conversation).filter(
            Conversation.conversation_uuid == conversation_id
        ).first()

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


@app.websocket("/ws/agent/queue")
async def websocket_agent_queue(websocket: WebSocket):
    """
    Agent dashboards connect here to receive a live push whenever a new
    conversation escalates, via _notify_escalation. No history is sent on
    connect - the dashboard fetches the current queue via GET /agent/queue
    on load, and this socket only carries live "a new one just arrived"
    events from then on.
    """
    await websocket.accept()
    queue_subscribers.append(websocket)
    try:
        while True:
            # This socket is push-only from the server's side; we still need
            # to await receive to detect disconnects.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in queue_subscribers:
            queue_subscribers.remove(websocket)


# -----------------------------------------
# Agent presence (online/busy/offline)
# -----------------------------------------

# Tracks which agent_id is connected to which presence socket, separate
# from the per-conversation chat sockets above.
agent_presence_connections: dict[int, WebSocket] = {}


async def _broadcast_presence(agent_id: int, status: str):
    """
    Placeholder broadcast hook for the future agent dashboard (Phase 3),
    which will want to see other agents' status update live. No dashboard
    listens yet, so this currently has no subscribers - safe no-op.
    """
    pass


@app.websocket("/ws/agent/{agent_id}")
async def websocket_agent_presence(websocket: WebSocket, agent_id: int):
    db = SessionLocal()
    try:
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            await websocket.close(code=4004)
            return

        await websocket.accept()
        agent_presence_connections[agent_id] = websocket

        agent.status = "online"
        db.commit()
        await _broadcast_presence(agent_id, "online")

        try:
            while True:
                # Agents can optionally send {"status": "busy"} or
                # {"status": "online"} to manually update their own state
                # (e.g. dashboard toggle), separate from chat activity.
                data = await websocket.receive_json()
                new_status = data.get("status")
                if new_status in ("online", "busy"):
                    agent.status = new_status
                    db.commit()
                    await _broadcast_presence(agent_id, new_status)
        except WebSocketDisconnect:
            pass
    finally:
        if agent_presence_connections.get(agent_id) is websocket:
            del agent_presence_connections[agent_id]
        agent.status = "offline"
        db.commit()
        db.close()


# -----------------------------------------
# Escalation helpers
# -----------------------------------------

def _escalate_conversation(db: Session, conversation: Conversation):
    """Flips a conversation to escalated status, if not already."""
    if conversation.status != "escalated":
        conversation.status = "escalated"
        db.commit()


async def _notify_escalation(conversation: Conversation, db: Session):
    """
    Pushes two live notifications when a conversation escalates:
    1. Into the conversation's own WebSocket room (so an agent already
       viewing that chat sees the status change).
    2. To every agent dashboard subscribed to /ws/agent/queue (so agents
       browsing the queue see the new entry appear without refreshing).
    """
    summary = _serialize_conversation_summary(conversation, db)

    await manager.broadcast(conversation.conversation_uuid, {
        "type": "escalation",
        "conversation_id": conversation.conversation_uuid,
        "status": "escalated",
    })

    for ws in list(queue_subscribers):
        try:
            await ws.send_json({"type": "new_escalation", "conversation": summary})
        except Exception:
            pass


def _check_consecutive_downvotes(db: Session, conversation_id: int) -> bool:
    """
    Returns True if the last CONSECUTIVE_DOWNVOTES_TO_ESCALATE assistant
    messages in this conversation were all rated 'down'.
    """
    recent_assistant_msgs = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id, Message.role == "assistant")
        .order_by(Message.id.desc())
        .limit(CONSECUTIVE_DOWNVOTES_TO_ESCALATE)
        .all()
    )

    if len(recent_assistant_msgs) < CONSECUTIVE_DOWNVOTES_TO_ESCALATE:
        return False

    for msg in recent_assistant_msgs:
        fb = db.query(Feedback).filter(Feedback.message_id == msg.id).first()
        if not fb or fb.rating != "down":
            return False

    return True


# -----------------------------------------
# Agent queue (Phase 3)
# -----------------------------------------

@app.get("/agent/queue")
def get_agent_queue(db: Session = Depends(get_db), agent_id: int = Depends(get_current_agent)):
    """
    Returns every escalated conversation that hasn't been resolved yet,
    newest first. Requires a valid agent session token - see
    dependencies.get_current_agent.
    """
    conversations = (
        db.query(Conversation)
        .filter(Conversation.status == "escalated", Conversation.ticket_status != "resolved")
        .order_by(Conversation.created_at.desc())
        .all()
    )
    return [_serialize_conversation_summary(c, db) for c in conversations]


class TicketStatusUpdate(BaseModel):
    ticket_status: str  # "open" | "in_progress" | "resolved"


@app.patch("/agent/conversation/{conversation_id}/status")
def update_ticket_status(
    conversation_id: str,
    payload: TicketStatusUpdate,
    db: Session = Depends(get_db),
    agent_id: int = Depends(get_current_agent),
):
    if payload.ticket_status not in ("open", "in_progress", "resolved"):
        raise HTTPException(status_code=400, detail="Invalid ticket_status value")

    conversation = db.query(Conversation).filter(
        Conversation.conversation_uuid == conversation_id
    ).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    conversation.ticket_status = payload.ticket_status
    db.commit()

    return {"conversation_id": conversation_id, "ticket_status": conversation.ticket_status}


@app.get("/agent/beneficiary/{university_id}")
def get_beneficiary_profile(
    university_id: str,
    db: Session = Depends(get_db),
    agent_id: int = Depends(get_current_agent),
):
    """
    Returns a student's name and their full conversation history across
    sessions (newest conversation first, messages oldest first within each).
    Only conversations linked to a logged-in student appear here; anonymous
    chats have no user_id and can't be attributed to anyone.
    """
    user = db.query(User).filter(User.university_id == university_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Beneficiary not found")

    conversations = (
        db.query(Conversation)
        .filter(Conversation.user_id == user.id)
        .order_by(Conversation.created_at.desc())
        .all()
    )

    history = []
    for c in conversations:
        messages = (
            db.query(Message)
            .filter(Message.conversation_id == c.id)
            .order_by(Message.id.asc())
            .all()
        )
        history.append({
            "conversation_id": c.conversation_uuid,
            "status": c.status,
            "ticket_status": c.ticket_status,
            "created_at": c.created_at.isoformat(),
            "messages": [_serialize_message(m) for m in messages],
        })

    return {
        "university_id": user.university_id,
        "name": user.name,
        "conversations": history,
    }


# -----------------------------------------
# Analytics (Phase 3)
# -----------------------------------------

# Mirrors the leaf questions in the frontend's categoryTree (ChatApp.jsx),
# mapped back to their top-level category. Used only for analytics grouping -
# if this drifts from the frontend tree, category counts just undercount
# rather than break anything.
LEAF_TO_CATEGORY = {
    "كيف أسجل دخولي للنظام؟": "الدخول والحسابات",
    "ما هو الرابط الصحيح لنظام البلاك بورد؟": "الدخول والحسابات",
    "نسيت كلمة السر": "الدخول والحسابات",
    "كلمة السر صحيحة ولكن النظام لا يعمل": "الدخول والحسابات",
    "كيف أغير كلمة المرور؟": "الدخول والحسابات",
    "كيف أقوم بتحديث بياناتي الشخصية؟": "الدخول والحسابات",
    "حسابي مقفل أو غير مفعل": "الدخول والحسابات",
    "أين أجد مقرراتي الدراسية؟": "الشؤون الأكاديمية",
    "محتوى المقرر أو المحاضرات لا تفتح": "الشؤون الأكاديمية",
    "كيف أتواصل مع أستاذ المقرر؟": "الشؤون الأكاديمية",
    "أضفت مقرر في البوابة ولم يظهر في البلاك بورد": "الشؤون الأكاديمية",
    "حذفت مقرر وما زال يظهر لي": "الشؤون الأكاديمية",
    "متى تتحدث المقررات في النظام؟": "الشؤون الأكاديمية",
    "أين أجد درجاتي للواجبات والاختبارات؟": "الشؤون الأكاديمية",
    "الدرجة غير ظاهرة لي": "الشؤون الأكاديمية",
    "كيف أعرف تفاصيل الدرجة والملاحظات؟": "الشؤون الأكاديمية",
    "يظهر لي (Access Denied)": "مشكلة تقنية عامة",
    "النظام معلق أو الصفحة لا تفتح": "مشكلة تقنية عامة",
    "لا أستطيع رفع الواجب أو الاختبار": "مشكلة تقنية عامة",
    "الملف المرفق حجمه كبير جداً": "مشكلة تقنية عامة",
    "لا أستطيع تحميل ملفات المقرر": "مشكلة تقنية عامة",
    ESCALATION_TRIGGER_TEXT: "مشكلة تقنية عامة",  # "مشكلة أخرى"
}


@app.get("/agent/analytics")
def get_analytics(db: Session = Depends(get_db), agent_id: int = Depends(get_current_agent)):
    """
    Dashboard stats: ticket counts by status, top categories (matched from
    each conversation's first user message), feedback totals, and a 7-day
    conversation-volume trend. Requires a valid agent session token.
    """
    all_conversations = db.query(Conversation).all()

    resolved_count = sum(1 for c in all_conversations if c.ticket_status == "resolved")
    active_count = sum(1 for c in all_conversations if c.ticket_status == "in_progress")
    unresolved_count = sum(
        1 for c in all_conversations
        if c.status == "escalated" and c.ticket_status == "open"
    )

    category_counter = Counter()
    for c in all_conversations:
        first_user_msg = (
            db.query(Message)
            .filter(Message.conversation_id == c.id, Message.role == "user")
            .order_by(Message.id.asc())
            .first()
        )
        if first_user_msg:
            category = LEAF_TO_CATEGORY.get(first_user_msg.content.strip())
            if category:
                category_counter[category] += 1

    top_categories = [
        {"category": cat, "count": count}
        for cat, count in category_counter.most_common(5)
    ]

    up_count = db.query(Feedback).filter(Feedback.rating == "up").count()
    down_count = db.query(Feedback).filter(Feedback.rating == "down").count()
    total_feedback = up_count + down_count
    down_rate = round((down_count / total_feedback) * 100, 1) if total_feedback else 0.0

    # Conversation volume for each of the last 7 days (including today),
    # oldest first - simple enough to drive a small bar/line chart.
    today = datetime.utcnow().date()
    traffic = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        count = sum(1 for c in all_conversations if c.created_at.date() == day)
        traffic.append({"date": day.isoformat(), "count": count})

    return {
        "resolved_count": resolved_count,
        "active_count": active_count,
        "unresolved_count": unresolved_count,
        "top_categories": top_categories,
        "feedback": {"up": up_count, "down": down_count, "down_rate_percent": down_rate},
        "traffic": traffic,
    }


@app.post("/agent/analytics/faq")
def generate_faq(db: Session = Depends(get_db), agent_id: int = Depends(get_current_agent)):
    """
    Reads recent real student questions and asks the local model to
    summarize the most common themes into a short FAQ. Excludes button-click
    text (exact category-tree matches and the escalation trigger) so it
    focuses on freely typed questions. Runs the AI on demand rather than on
    a schedule - this can take a while on CPU-only hardware.
    """
    known_leaf_texts = set(LEAF_TO_CATEGORY.keys())

    recent_user_messages = (
        db.query(Message)
        .filter(Message.role == "user")
        .order_by(Message.id.desc())
        .limit(200)
        .all()
    )

    questions = []
    seen = set()
    for m in recent_user_messages:
        text = m.content.strip()
        if text in known_leaf_texts or text in seen or not text:
            continue
        seen.add(text)
        questions.append(text)

    faq_text = generate_faq_summary(questions)
    return {"faq": faq_text, "questions_analyzed": len(questions)}


@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(
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

    # Always persist the user's message first, regardless of AI/escalated path.
    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=request.question,
    )
    db.add(user_message)
    db.commit()

    # Trigger 1: user explicitly asked for "أخرى (اكتب مشكلتك)" -> escalate now.
    just_escalated = False
    if request.question.strip() == ESCALATION_TRIGGER_TEXT and conversation.status != "escalated":
        _escalate_conversation(db, conversation)
        just_escalated = True

    if just_escalated:
        await _notify_escalation(conversation, db)

    # If this conversation is (now, or already) escalated, a human should be
    # answering - skip the AI entirely and just acknowledge/save.
    if conversation.status == "escalated":
        reply = ESCALATION_REPLY if just_escalated else (
            "طلبك قيد المراجعة من قبل فريق الدعم. / Your request is being handled by our support team."
        )
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
            status=conversation.status,
        )

    # Normal AI path (not escalated).
    history_rows = (
        db.query(Message)
        .filter(Message.conversation_id == conversation.id)
        .order_by(Message.id.desc())
        .limit(MAX_HISTORY_MESSAGES)
        .all()
    )
    history_rows.reverse()
    history = [{"role": m.role, "content": m.content} for m in history_rows]

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
        status=conversation.status,
    )


@app.post("/api/feedback", response_model=FeedbackResponse)
async def feedback_endpoint(request: FeedbackRequest, db: Session = Depends(get_db)):
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

    # Trigger 2: 2+ consecutive 👎 on assistant replies -> escalate.
    if request.rating == "down":
        conversation = db.query(Conversation).filter(
            Conversation.id == message.conversation_id
        ).first()
        if conversation and conversation.status != "escalated":
            if _check_consecutive_downvotes(db, conversation.id):
                _escalate_conversation(db, conversation)
                await _notify_escalation(conversation, db)

    return FeedbackResponse(message_id=request.message_id, rating=request.rating)
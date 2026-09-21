from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from database import Base
from datetime import datetime
import uuid

class User(Base):
    __tablename__ = "users"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    university_id = Column(String, unique=True, index=True)
    name = Column(String)

class UserSession(Base):
    __tablename__ = "user_sessions"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"))
    expires_at = Column(DateTime)

class Agent(Base):
    __tablename__ = "agents"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    status = Column(String, default="offline")  # "online" | "busy" | "offline"

class AgentSession(Base):
    __tablename__ = "agent_sessions"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True, default=lambda: str(uuid.uuid4()))
    agent_id = Column(Integer, ForeignKey("agents.id"))
    expires_at = Column(DateTime)


# -----------------------------------------
# Conversational memory & feedback logging
# -----------------------------------------

class Conversation(Base):
    """
    One row per chat session/thread. A conversation is identified externally
    by conversation_uuid (never the raw integer id) so the frontend can hold
    a stable reference without ever seeing internal database keys.
    """
    __tablename__ = "conversations"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    conversation_uuid = Column(String, unique=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # nullable: chat can start before/without login
    status = Column(String, default="ai")  # "ai" | "escalated" | "closed" (escalated/closed reserved for the handoff feature)
    ticket_status = Column(String, default="open")  # "open" | "in_progress" | "resolved" — support-ticket lifecycle, separate from status (which drives AI vs human routing)
    created_at = Column(DateTime, default=datetime.utcnow)


class Message(Base):
    """
    Every user, assistant, and agent turn in a conversation. Kept in
    insertion order via id, which is also used to reconstruct history for
    the LLM prompt and for the live agent handoff / beneficiary profile view.
    """
    __tablename__ = "messages"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), index=True)
    role = Column(String)  # "user" | "assistant" | "agent"
    agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True)  # set only when role == "agent"
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class Feedback(Base):
    """
    One row per rated assistant message. message_id is unique so re-voting
    updates the existing rating instead of creating duplicates.
    """
    __tablename__ = "feedback"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id"), unique=True, index=True)
    rating = Column(String)  # "up" | "down"
    created_at = Column(DateTime, default=datetime.utcnow)
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from database import Base
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

class AgentSession(Base):
    __tablename__ = "agent_sessions"
    __table_args__ = {'extend_existing': True}
    
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True, default=lambda: str(uuid.uuid4()))
    agent_id = Column(Integer, ForeignKey("agents.id"))
    expires_at = Column(DateTime)
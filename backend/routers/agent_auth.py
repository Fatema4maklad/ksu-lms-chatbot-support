from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timedelta
import uuid
from passlib.hash import bcrypt

from database import get_db, FakeDB
from models import Agent, AgentSession
from schemas import AgentLoginRequest, AgentLoginResponse

router = APIRouter()

SESSION_TTL_HOURS = 12  # shorter than student sessions, agents are on shift-based access

@router.post("/agent/login", response_model=AgentLoginResponse)
def agent_login(payload: AgentLoginRequest, db: FakeDB = Depends(get_db)):
    agent = db.query_agent_by_email(payload.email)

    if agent is None or not bcrypt.verify(payload.password, agent.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    session = AgentSession(
        token=str(uuid.uuid4()),
        agent_id=agent.id,
        expires_at=datetime.utcnow() + timedelta(hours=SESSION_TTL_HOURS)
    )
    db.add_agent_session(session)

    return AgentLoginResponse(
        session_token=session.token,
        agent_id=str(agent.id),
        name=agent.name
    )
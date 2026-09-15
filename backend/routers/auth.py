from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import bcrypt
import uuid

from database import get_db
from models import User, UserSession, Agent, AgentSession
from schemas import LoginRequest, LoginResponse, AgentLoginRequest, AgentLoginResponse

router = APIRouter()

# -----------------------------------------
# 1. USER LOGIN (Students & Instructors)
# -----------------------------------------
@router.post("/auth/login", response_model=LoginResponse)
def user_login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.university_id == payload.university_id).first()

    if not user:
        user = User(university_id=payload.university_id, name=payload.name)
        db.add(user)
        db.commit()
        db.refresh(user)
    elif user.name != payload.name:
        user.name = payload.name
        db.commit()
        db.refresh(user)

    session = UserSession(
        token=str(uuid.uuid4()),
        user_id=user.id,
        expires_at=datetime.utcnow() + timedelta(hours=24)
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return LoginResponse(
        session_token=session.token,
        university_id=user.university_id,
        name=user.name
    )

# -----------------------------------------
# 2. AGENT LOGIN (Support Staff)
# -----------------------------------------
@router.post("/agent/login", response_model=AgentLoginResponse)
def agent_login(payload: AgentLoginRequest, db: Session = Depends(get_db)):
    agent = db.query(Agent).filter(Agent.email == payload.email).first()

    if not agent or not bcrypt.checkpw(payload.password.encode(), agent.password_hash.encode()):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Mark the agent online as soon as they authenticate successfully.
    # The /ws/agent/{agent_id} presence socket (connected right after
    # login) will keep this in sync going forward, including setting it
    # back to "offline" automatically on disconnect.
    agent.status = "online"
    db.commit()

    session = AgentSession(
        token=str(uuid.uuid4()),
        agent_id=agent.id,
        expires_at=datetime.utcnow() + timedelta(hours=12)
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return AgentLoginResponse(
        session_token=session.token,
        agent_id=str(agent.id),
        name=agent.name
    )
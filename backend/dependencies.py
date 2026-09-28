from fastapi import Header, HTTPException, Depends
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from database import get_db
from models import UserSession, AgentSession


def get_current_user(x_session_token: str = Header(...), db: Session = Depends(get_db)):
    session = db.query(UserSession).filter(
        UserSession.token == x_session_token,
        UserSession.expires_at > datetime.utcnow()
    ).first()
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return session.user_id


def get_optional_current_user(
    x_session_token: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> Optional[int]:
    """
    Like get_current_user, but never raises. Used by endpoints (like /api/chat)
    that should work for anonymous visitors but still link a conversation to a
    logged-in user's account whenever a valid session token is present.
    """
    if not x_session_token:
        return None
    session = db.query(UserSession).filter(
        UserSession.token == x_session_token,
        UserSession.expires_at > datetime.utcnow()
    ).first()
    return session.user_id if session else None


def get_current_agent(x_session_token: str = Header(...), db: Session = Depends(get_db)) -> int:
    """
    Requires a valid, non-expired AgentSession token. Used to protect
    agent-only endpoints (e.g. the escalation queue) so student conversation
    data isn't reachable without a logged-in agent.
    """
    session = db.query(AgentSession).filter(
        AgentSession.token == x_session_token,
        AgentSession.expires_at > datetime.utcnow()
    ).first()
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired agent session")
    return session.agent_id

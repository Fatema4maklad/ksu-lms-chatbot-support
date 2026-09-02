from fastapi import Header, HTTPException, Depends
from datetime import datetime
from sqlalchemy.orm import Session

from database import get_db
from models import UserSession

def get_current_user(x_session_token: str = Header(...), db: Session = Depends(get_db)):
    session = db.query(UserSession).filter(
        UserSession.token == x_session_token,
        UserSession.expires_at > datetime.utcnow()
    ).first()
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return session.user_id
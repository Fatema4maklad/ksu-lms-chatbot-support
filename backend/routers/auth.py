from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timedelta
import uuid

from database import get_db, FakeDB
from models import User, UserSession
from schemas import LoginRequest, LoginResponse

router = APIRouter()

SESSION_TTL_HOURS = 24

@router.post("/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: FakeDB = Depends(get_db)):
    user = db.query_user_by_university_id(payload.university_id)

    if user is None:
        user = User(name=payload.name, university_id=payload.university_id)
        db.add_user(user)
    else:
        if user.name.strip().lower() != payload.name.strip().lower():
            raise HTTPException(status_code=401, detail="Name does not match university ID on record")

    session = UserSession(
        token=str(uuid.uuid4()),
        user_id=user.id,
        expires_at=datetime.utcnow() + timedelta(hours=SESSION_TTL_HOURS)
    )
    db.add_session(session)

    return LoginResponse(
        session_token=session.token,
        user_id=str(user.id),
        name=user.name
    )
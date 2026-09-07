from pydantic import BaseModel
from typing import Optional

class LoginRequest(BaseModel):
    name: str
    university_id: str

class LoginResponse(BaseModel):
    session_token: str
    university_id: str
    name: str

class AgentLoginRequest(BaseModel):
    email: str
    password: str

class AgentLoginResponse(BaseModel):
    session_token: str
    agent_id: str
    name: str


# -----------------------------------------
# Chat & feedback
# -----------------------------------------

class ChatRequest(BaseModel):
    # NOTE: field name must stay "question" — the React frontend depends on
    # this exact key to avoid a 422 Unprocessable Content error.
    question: str
    conversation_id: Optional[str] = None  # conversation_uuid; omit/None to start a new thread

class ChatResponse(BaseModel):
    answer: str
    conversation_id: str
    message_id: int  # id of the assistant's message; needed to submit feedback on it

class FeedbackRequest(BaseModel):
    message_id: int
    rating: str  # "up" or "down"

class FeedbackResponse(BaseModel):
    message_id: int
    rating: str
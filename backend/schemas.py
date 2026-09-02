from pydantic import BaseModel

class LoginRequest(BaseModel):
    name: str
    university_id: str

class LoginResponse(BaseModel):
    session_token: str
    user_id: str
    name: str
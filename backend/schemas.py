from pydantic import BaseModel

class LoginRequest(BaseModel):
    name: str
    university_id: str

class LoginResponse(BaseModel):
    session_token: str
    user_id: str
    name: str

class AgentLoginRequest(BaseModel):
    email: str
    password: str

class AgentLoginResponse(BaseModel):
    session_token: str
    agent_id: str
    name: str
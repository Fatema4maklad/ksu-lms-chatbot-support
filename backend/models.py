import uuid
from datetime import datetime

class User:
    def __init__(self, name: str, university_id: str):
        self.id = uuid.uuid4()
        self.name = name
        self.university_id = university_id

class UserSession:
    def __init__(self, token: str, user_id, expires_at: datetime):
        self.token = token
        self.user_id = user_id
        self.expires_at = expires_at

class Agent:
    def __init__(self, name: str, email: str, password_hash: str):
        self.id = uuid.uuid4()
        self.name = name
        self.email = email
        self.password_hash = password_hash

class AgentSession:
    def __init__(self, token: str, agent_id, expires_at: datetime):
        self.token = token
        self.agent_id = agent_id
        self.expires_at = expires_at
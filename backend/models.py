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
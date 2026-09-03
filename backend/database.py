# TEMPORARY MOCK — replace once teammate's real DB layer is ready.

_users = []
_sessions = []
_agents = []
_agent_sessions = []

class FakeDB:
    def query_user_by_university_id(self, university_id):
        for u in _users:
            if u.university_id == university_id:
                return u
        return None

    def add_user(self, user):
        _users.append(user)
    def query_agent_by_email(self, email):
        for a in _agents:
            if a.email == email:
                return a
        return None

    def add_agent(self, agent):
        _agents.append(agent)

    def add_agent_session(self, session):
        _agent_sessions.append(session)

    def query_agent_session_by_token(self, token):
        for s in _agent_sessions:
            if s.token == token:
                return s
        return None
    def add_session(self, session):
        _sessions.append(session)

def get_db():
    yield FakeDB()

def _seed():
    from models import Agent
    from passlib.hash import bcrypt
    if not _agents:
        _agents.append(Agent(name="Test Agent", email="agent@ksu.edu.sa", password_hash=bcrypt.hash("test1234")))

_seed()
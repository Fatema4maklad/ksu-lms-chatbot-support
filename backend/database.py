# TEMPORARY MOCK — replace once teammate's real DB layer is ready.

_users = []
_sessions = []

class FakeDB:
    def query_user_by_university_id(self, university_id):
        for u in _users:
            if u.university_id == university_id:
                return u
        return None

    def add_user(self, user):
        _users.append(user)

    def add_session(self, session):
        _sessions.append(session)

def get_db():
    yield FakeDB()
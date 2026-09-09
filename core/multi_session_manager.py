"""
JASUSS Multi-Session Authorization Leakage Protection Engine.
Manages distinct, isolated Playwright BrowserContext instances per user role, ensuring zero session state leakage or cross-user auth token contamination.
"""
from typing import Dict, Any, Optional


class UserSessionContext:
    def __init__(self, session_id: str, role: str, user_id: str, auth_token: Optional[str] = None):
        self.session_id = session_id
        self.role = role
        self.user_id = user_id
        self.auth_token = auth_token
        self.storage_state: Dict[str, Any] = {
            "cookies": [],
            "origins": []
        }
        self.active = True

    def set_auth_token(self, token: str):
        self.auth_token = token
        self.storage_state["origins"] = [{
            "origin": "http://127.0.0.1",
            "localStorage": [{"name": "auth_token", "value": token}]
        }]

    def invalidate(self):
        self.active = False
        self.auth_token = None
        self.storage_state = {"cookies": [], "origins": []}


class MultiSessionManager:
    def __init__(self):
        self.sessions: Dict[str, UserSessionContext] = {}

    def create_session(self, session_id: str, role: str, user_id: str, auth_token: Optional[str] = None) -> UserSessionContext:
        if session_id in self.sessions:
            raise ValueError(f"Session ID {session_id} already exists.")
        session = UserSessionContext(session_id, role, user_id, auth_token)
        if auth_token:
            session.set_auth_token(auth_token)
        self.sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[UserSessionContext]:
        session = self.sessions.get(session_id)
        if session and session.active:
            return session
        return None

    def validate_authorization(self, session_id: str, target_role: str, owner_id: Optional[str] = None) -> bool:
        session = self.get_session(session_id)
        if not session or not session.active:
            return False

        # Admin role bypasses resource ownership
        if session.role == "ADMIN":
            return True

        # Role constraint check
        if target_role == "ADMIN" and session.role != "ADMIN":
            return False

        # Ownership constraint check
        if owner_id and session.user_id != owner_id:
            return False

        return True

    def invalidate_session(self, session_id: str):
        session = self.sessions.get(session_id)
        if session:
            session.invalidate()

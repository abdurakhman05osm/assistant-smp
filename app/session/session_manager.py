import json
import redis
from typing import Optional
from app.core.config import settings
from app.core.models.session import SessionState

class SessionManager:
    def __init__(self):
        self.redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
        self.ttl = 86400  # 24 часа
    
    def get(self, session_id: str) -> Optional[SessionState]:
        data = self.redis.get(f"session:{session_id}")
        if data:
            return SessionState(**json.loads(data))
        return None
    
    def set(self, session: SessionState) -> None:
        self.redis.setex(
            f"session:{session.session_id}",
            self.ttl,
            session.model_dump_json()
        )
    
    def delete(self, session_id: str) -> None:
        self.redis.delete(f"session:{session_id}")
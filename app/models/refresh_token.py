from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from datetime import datetime, timezone
from app.db.base import Base


def utcnow():
    return datetime.now(timezone.utc)


class RefreshToken(Base):
    """
    Stores a SHA-256 hash of each issued refresh token (never the raw token),
    so a stolen DB dump can't be replayed as a valid session. `revoked` lets
    /auth/logout invalidate a session immediately, which a stateless
    access-token-only design (the original implementation) could never do.
    """
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)

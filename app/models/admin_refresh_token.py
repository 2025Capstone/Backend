from sqlalchemy import Column, Integer, String, DateTime, Boolean
from app.db.base import Base

class AdminRefreshToken(Base):
    __tablename__ = "admin_refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(512), unique=True, nullable=False)
    is_revoked = Column(Boolean, default=False)
    created_at = Column(DateTime)
    expired_at = Column(DateTime)

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.db.base import Base

class InstructorRefreshToken(Base):
    __tablename__ = "instructor_refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(512), unique=True, nullable=False)
    instructor_id = Column(Integer, ForeignKey("instructor.id"), nullable=False)
    is_revoked = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    expired_at = Column(DateTime)

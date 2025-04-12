from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from app.db.base import Base

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(512), unique=True, nullable=False)
    student_uid = Column(String(128), ForeignKey("student.uid"), nullable=False)
    is_revoked = Column(Boolean, default=False)
    created_at = Column(DateTime)
    expired_at = Column(DateTime)
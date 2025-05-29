from sqlalchemy import Column, String, Integer, Boolean, ForeignKey
from app.db.base import Base

class DrowsinessSession(Base):
    __tablename__ = "drowsiness_session"

    session_id = Column(String(64), primary_key=True)
    student_uid = Column(String(128), ForeignKey("student.uid"), nullable=False)
    video_id = Column(Integer, ForeignKey("video.id"), nullable=False)
    auth_code = Column(String(6), nullable=False)
    verified = Column(Boolean, default=False)

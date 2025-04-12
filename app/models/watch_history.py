from sqlalchemy import Column, Integer, ForeignKey, TIMESTAMP, func
from app.db.base import Base

class WatchHistory(Base):
    __tablename__ = "watch_history"

    student_id = Column(Integer, ForeignKey("student.id"), primary_key=True)
    video_id = Column(Integer, ForeignKey("video.id"), primary_key=True)
    timestamp = Column(TIMESTAMP, server_default=func.now())
# /app/models/watch_history.py (또는 해당 모델 파일)
# String 타입 import 추가
from sqlalchemy import Column, Integer, ForeignKey, TIMESTAMP, func, String
from sqlalchemy.orm import relationship
from app.db.base import Base

class WatchHistory(Base):
    __tablename__ = "watch_history"


    student_uid = Column(String(128), ForeignKey("student.uid"), primary_key=True)
    video_id = Column(Integer, ForeignKey("video.id"), primary_key=True)
    watched_percent = Column(Integer, nullable=False, default=0)  # 0~100
    timestamp = Column(TIMESTAMP, server_default=func.now())

    # Video 모델과의 관계 추가
    video = relationship("Video", backref="watch_histories")
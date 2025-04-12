from sqlalchemy import Column, Integer, Float, ForeignKey, TIMESTAMP, func
from app.db.base import Base

class DrowsinessLevel(Base):
    __tablename__ = "drowsiness_level"

    video_id = Column(Integer, ForeignKey("video.id"), primary_key=True)
    student_id = Column(Integer, ForeignKey("student.id"), primary_key=True)
    timestamp = Column(Integer, nullable=False)  # 영상 내 몇 초인지
    drowsiness_score = Column(Float, nullable=False)  # 졸음 점수 (0~1)
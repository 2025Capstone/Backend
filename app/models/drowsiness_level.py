# /app/models/drowsiness_level.py (또는 해당 모델 파일)
# String 타입 import 추가
from sqlalchemy import Column, Integer, Float, ForeignKey, TIMESTAMP, func, String
from app.db.base import Base

class DrowsinessLevel(Base):
    __tablename__ = "drowsiness_level"

    video_id = Column(Integer, ForeignKey("video.id"), primary_key=True)
    student_uid = Column(String(128), ForeignKey("student.uid"), primary_key=True)
    timestamp = Column(Integer, nullable=False)  # 영상 내 몇 초인지
    drowsiness_score = Column(Float, nullable=False)  # 졸음 점수 (0~1)

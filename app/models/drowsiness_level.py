# /app/models/drowsiness_level.py (또는 해당 모델 파일)
# String 타입 import 추가
from sqlalchemy import Column, Integer, Float, ForeignKey, TIMESTAMP, func, String
from app.db.base import Base

class DrowsinessLevel(Base):
    __tablename__ = "drowsiness_level"

    id            = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    video_id = Column(Integer, ForeignKey("video.id"), nullable=False)
    student_uid = Column(String(128), ForeignKey("student.uid"), nullable=False)
    timestamp = Column(Integer, nullable=False)  # 영상 내 몇 분인지
    drowsiness_score = Column(Float, nullable=False)  # 졸음 점수 (1~5)

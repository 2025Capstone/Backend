# /app/models/enrollment.py (또는 해당 모델 파일)
# String 타입 import 추가
from sqlalchemy import Column, Integer, ForeignKey, TIMESTAMP, func, String
from app.db.base import Base

class Enrollment(Base):
    __tablename__ = "enrollment"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lecture_id = Column(Integer, ForeignKey("lecture.id"), nullable=False)
    student_uid = Column(String(128), ForeignKey("student.uid"), nullable=False)
    enrolled_at = Column(TIMESTAMP, server_default=func.now())
# /app/models/drowsiness_level.py (또는 해당 모델 파일)
# String 타입 import 추가
from sqlalchemy import Column, Integer, Float, ForeignKey, TIMESTAMP, func, String
from app.db.base import Base

class DrowsinessLevel(Base):
    __tablename__ = "drowsiness_level"

    video_id = Column(Integer, ForeignKey("video.id"), primary_key=True)

    # --- student_id 컬럼 수정 ---
    # 기존 정의 주석 처리
    # student_id = Column(Integer, ForeignKey("student.id"), primary_key=True)
    # 새 정의: 이름 변경, 타입 String, ForeignKey는 student.uid 참조
    student_uid = Column(String(128), ForeignKey("student.uid"), primary_key=True)
    # -------------------------

    timestamp = Column(Integer, nullable=False)  # 영상 내 몇 초인지
    drowsiness_score = Column(Float, nullable=False)  # 졸음 점수 (0~1)

    # 만약 Student 모델과 relationship이 정의되어 있었다면,
    # foreign_keys 인자 등을 [DrowsinessLevel.student_uid] 로 맞춰주어야 합니다.
    # 예: student = relationship("Student", foreign_keys=[student_uid], ...)
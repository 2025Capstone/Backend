from sqlalchemy import Column, Integer, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.db.base import Base

class Lecture(Base):
    __tablename__ = "lecture"

    id = Column(Integer, primary_key=True, index=True)
    instructor_id = Column(Integer, ForeignKey("instructor.id"), nullable=False)
    name = Column(String(255), nullable=False)
    is_public = Column(Boolean, nullable=False, default=True)
    # 강의 요일/시간 예: '월요일 14:00~17:00'
    schedule = Column(String(100), nullable=True)
    # 강의실 정보 예: 'N14-104'
    classroom = Column(String(50), nullable=True)

    instructor = relationship("Instructor", backref="lectures")
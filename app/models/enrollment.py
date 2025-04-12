from sqlalchemy import Column, Integer, ForeignKey, TIMESTAMP, func
from app.db.base import Base

class Enrollment(Base):
    __tablename__ = "enrollment"

    lecture_id = Column(Integer, ForeignKey("lecture.id"), primary_key=True)
    student_id = Column(Integer, ForeignKey("student.id"), primary_key=True)
    enrolled_at = Column(TIMESTAMP, server_default=func.now())
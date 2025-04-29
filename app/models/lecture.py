from sqlalchemy import Column, Integer, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.db.base import Base

class Lecture(Base):
    __tablename__ = "lecture"

    id = Column(Integer, primary_key=True, index=True)
    instructor_id = Column(Integer, ForeignKey("instructor.id"), nullable=False)
    name = Column(String(255), nullable=False)
    is_public = Column(Boolean, nullable=False, default=True)

    instructor = relationship("Instructor", backref="lectures")
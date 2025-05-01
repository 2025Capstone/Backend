from sqlalchemy import Column, Integer, String
from app.db.base import Base

class Instructor(Base):
    __tablename__ = "instructor"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    is_approved = Column(Integer, default=0, nullable=False, comment="관리자 승인 여부 (0=미승인, 1=승인)")
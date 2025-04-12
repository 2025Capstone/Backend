from sqlalchemy import Column, Integer, String
from app.db.base import Base

class Instructor(Base):
    __tablename__ = "instructor"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password = Column(String(255), nullable=False)  # 해시된 비밀번호 저장
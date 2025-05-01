from sqlalchemy import Column, Integer, String
from app.db.base import Base

class Admin(Base):
    __tablename__ = "admin"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False)
    password = Column(String(255), nullable=False)  # 해시된 비밀번호 저장

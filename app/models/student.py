# /app/models/student.py
from sqlalchemy import Column, String, Boolean # Boolean은 예시, 필요시 다른 타입 사용
# Integer는 다른 테이블 FK 참조용으로 남겨둘 수 있으나, 여기서는 uid를 PK로 사용
from app.db.base import Base # base_class 경로 확인

class Student(Base):
    __tablename__ = "student"

    uid = Column(String(128), primary_key=True, index=True)
    name = Column(String(255), nullable=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    profile_image_url = Column(String(512), nullable=True, comment="S3에 저장된 프로필 이미지 URL")

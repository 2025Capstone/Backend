# /app/models/student.py
from sqlalchemy import Column, String, Boolean # Boolean은 예시, 필요시 다른 타입 사용
# Integer는 다른 테이블 FK 참조용으로 남겨둘 수 있으나, 여기서는 uid를 PK로 사용
from app.db.base import Base # base_class 경로 확인

class Student(Base):
    __tablename__ = "student"

    # id 컬럼 제거 또는 주석 처리
    # id = Column(Integer, primary_key=True, index=True)

    # Firebase UID를 기본 키로 사용
    uid = Column(String(128), primary_key=True, index=True) # 길이 확인 (128 권장)

    # name은 nullable=True로 변경 (Firebase에서 이름은 선택 사항)
    name = Column(String(255), nullable=True)

    # email은 unique=True 유지, index 추가 권장
    email = Column(String(255), unique=True, index=True, nullable=False)

    # password 컬럼 제거
    # password = Column(String(255), nullable=False)

    # 만약 다른 테이블에서 student.id를 참조했다면,
    # 해당 테이블의 외래 키 컬럼도 String(128) 타입으로 변경하고
    # student.uid를 참조하도록 Alembic 마이그레이션에서 수정해야 합니다.
    # 예: enrollments = relationship("Enrollment", back_populates="student", foreign_keys="[Enrollment.student_uid]")
# /app/services/student_service.py
from sqlalchemy.orm import Session
from typing import Optional

from app.models.student import Student
# 업데이트된 스키마 사용
from app.schemas.student import StudentCreate # uid, email, name 포함

def create_student(db: Session, *, student_in: StudentCreate) -> Student:
    """ Firebase 정보 기반으로 학생 생성 """
    # password 관련 로직 제거됨
    db_student = Student(
        uid=student_in.uid,
        name=student_in.name,
        email=student_in.email
    )
    db.add(db_student)
    db.commit()
    db.refresh(db_student)
    return db_student

def get_student_by_uid(db: Session, student_uid: str) -> Optional[Student]:
    """ UID로 학생 조회 """
    return db.query(Student).filter(Student.uid == student_uid).first()

def get_student_by_email(db: Session, email: str) -> Optional[Student]:
     """ Email로 학생 조회 (중복 확인용) """
     return db.query(Student).filter(Student.email == email).first()

# 기존 get_student(db, student_id) 함수는 더 이상 필요 없을 수 있음
# def get_student(db: Session, student_id: int):
#     return db.query(Student).filter(Student.id == student_id).first()
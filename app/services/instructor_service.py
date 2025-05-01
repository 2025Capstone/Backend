from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from passlib.hash import bcrypt
from app.models.instructor import Instructor
from app.schemas.instructor_auth import InstructorCreate, InstructorCreateResponse

def create_instructor(db: Session, instructor_in: InstructorCreate) -> InstructorCreateResponse:
    # 이메일 중복 체크
    if db.query(Instructor).filter(Instructor.email == instructor_in.email).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 존재하는 이메일입니다.")

    hashed_password = bcrypt.hash(instructor_in.password)
    new_instructor = Instructor(
        name=instructor_in.name,
        email=instructor_in.email,
        password=hashed_password,
        is_approved=0  # 회원가입 시 기본값 0
    )
    db.add(new_instructor)
    db.commit()
    db.refresh(new_instructor)
    return InstructorCreateResponse(
        id=new_instructor.id,
        name=new_instructor.name,
        email=new_instructor.email,
        message="Instructor successfully registered."
    )

def approve_instructor_by_id(db: Session, instructor_id: int):
    instructor = db.query(Instructor).filter(Instructor.id == instructor_id).first()
    if not instructor:
        raise HTTPException(status_code=404, detail="Instructor not found.")
    instructor.is_approved = 1
    db.commit()
    db.refresh(instructor)
    return {
        "id": instructor.id,
        "name": instructor.name,
        "email": instructor.email,
        "is_approved": instructor.is_approved,
        "message": "Instructor approved successfully."
    }

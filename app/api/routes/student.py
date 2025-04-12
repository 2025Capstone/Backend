from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.schemas.student import StudentCreate, Student
from app.services.student_service import create_student, get_student
from app.dependencies.db import get_db

router = APIRouter()

@router.post("/", response_model=Student)
def register_student(student: StudentCreate, db: Session = Depends(get_db)):
    return create_student(db, student)

@router.get("/{student}", response_model=Student)
def read_student(student_id: int, db: Session = Depends(get_db)):
    return get_student(db, student_id)
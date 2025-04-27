from fastapi import APIRouter, Depends, Body, HTTPException
from sqlalchemy.orm import Session
from app.dependencies.db import get_db
from app.dependencies.auth import get_current_instructor_id
from app.schemas.instructor import LectureCreate, LectureCreateResponse
from app.services.instructor import create_lecture_for_instructor

router = APIRouter()

@router.post("/lectures", response_model=LectureCreateResponse, summary="강의 생성 (강의자)")
def create_lecture(
    lecture_in: LectureCreate = Body(...),
    db: Session = Depends(get_db),
    instructor_id: int = Depends(get_current_instructor_id)
):
    """
    강의자가 강의를 생성합니다.
    (instructor_id는 이제 JWT access token에서 추출됩니다)
    """
    return create_lecture_for_instructor(db, instructor_id, lecture_in)
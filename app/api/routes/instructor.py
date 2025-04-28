from fastapi import APIRouter, Depends, Body, HTTPException
from sqlalchemy.orm import Session
from app.dependencies.db import get_db
from app.dependencies.auth import get_current_instructor_id
from app.schemas.instructor import LectureCreate, LectureCreateResponse, MyLectureListResponse
from app.services.instructor import create_lecture_for_instructor, get_my_lectures

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

@router.get("/lectures", response_model=MyLectureListResponse, summary="내 강의 목록 조회")
def get_my_lecture_list(
    db: Session = Depends(get_db),
    instructor_id: int = Depends(get_current_instructor_id)
):
    """
    강의자가 본인 토큰으로 자신의 강의 목록을 조회합니다.
    """
    lectures = get_my_lectures(db, instructor_id)
    return MyLectureListResponse(lectures=lectures)
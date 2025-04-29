from fastapi import APIRouter, Depends, Body, HTTPException
from sqlalchemy.orm import Session
from app.dependencies.db import get_db
from app.dependencies.auth import get_current_instructor_id
from app.schemas.instructor import LectureCreate, LectureCreateResponse, MyLectureListResponse, LectureStudentListRequest, LectureStudentListResponse
from app.schemas.lecture import LectureVisibilityUpdateRequest, LectureVisibilityUpdateResponse
from app.services.instructor import create_lecture_for_instructor, get_my_lectures, get_students_for_my_lecture
from app.models.lecture import Lecture

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

@router.post("/lecture/students", response_model=LectureStudentListResponse, summary="내 강의 수강생 목록 조회")
def get_my_lecture_students(
    req: LectureStudentListRequest = Body(...),
    db: Session = Depends(get_db),
    instructor_id: int = Depends(get_current_instructor_id)
):
    """
    강의자가 본인 강의의 수강생 목록을 조회합니다.
    - 본인 강의가 아니면 403 반환
    """
    students = get_students_for_my_lecture(db, instructor_id, req.lecture_id)
    return LectureStudentListResponse(students=students)

@router.patch("/lectures/visibility", response_model=LectureVisibilityUpdateResponse, summary="강의 공개여부 수정")
def update_lecture_visibility(
    req: LectureVisibilityUpdateRequest = Body(...),
    db: Session = Depends(get_db),
    instructor_id: int = Depends(get_current_instructor_id)
):
    """
    강의자가 본인 소유의 강의의 공개/비공개 여부를 수정합니다.
    """
    lecture = db.query(Lecture).filter(Lecture.id == req.lecture_id).first()
    if not lecture:
        raise HTTPException(status_code=404, detail="해당 강의를 찾을 수 없습니다.")
    if lecture.instructor_id != instructor_id:
        raise HTTPException(status_code=403, detail="본인 소유의 강의만 수정할 수 있습니다.")
    lecture.is_public = req.is_public
    db.commit()
    db.refresh(lecture)
    return LectureVisibilityUpdateResponse(
        id=lecture.id,
        is_public=lecture.is_public,
        message="공개여부가 성공적으로 변경되었습니다."
    )
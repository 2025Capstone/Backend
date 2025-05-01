from fastapi import APIRouter, Depends,  Body
from sqlalchemy.orm import Session
from app.dependencies.db import get_db
from app.schemas.instructor_auth import  InstructorCreateResponse
from app.services.instructor_service import approve_instructor_by_id
from app.services.admin_service import create_lecture_by_admin
from app.dependencies.admin_auth import  get_current_admin_token
from app.schemas.instructor import AdminLectureCreate, LectureCreateResponse

router = APIRouter(
    dependencies=[Depends(get_current_admin_token)]
)


@router.post("/approve-instructor/{instructor_id}", summary="교수자 승인", response_model=InstructorCreateResponse)
def approve_instructor(
    instructor_id: int,
    db: Session = Depends(get_db)
):
    """
    교수자 승인 (관리자 권한 필요)
    """
    result = approve_instructor_by_id(db, instructor_id)
    return InstructorCreateResponse(
        id=result["id"],
        name=result["name"],
        email=result["email"],
        message=result["message"]
    )


@router.post("/lectures", response_model=LectureCreateResponse, summary="강의 생성 (관리자)")
def create_lecture_by_admin_api(
    lecture_in: AdminLectureCreate = Body(...),
    db: Session = Depends(get_db)
):
    """
    관리자가 강의명, 시간표, 강의실, 강의자(instructor_id)까지 지정하여 강의를 생성합니다.
    """
    return create_lecture_by_admin(db, lecture_in)

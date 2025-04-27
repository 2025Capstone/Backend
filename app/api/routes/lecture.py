from fastapi import APIRouter, Depends, Body
from app.models.lecture import Lecture
from app.models.instructor import Instructor
from app.schemas.lecture import LectureListResponse, LectureBase
from app.services.auth_service import get_current_student
from sqlalchemy.orm import Session
from app.dependencies.db import get_db
from app.dependencies.auth import get_current_student_uid
from app.schemas.student import EnrollmentRequest, EnrollmentResponse
from app.services.student import enroll_student_in_lecture


router = APIRouter(
    dependencies=[Depends(get_current_student)]
)

@router.get("", response_model=LectureListResponse, description="강의 목록 조회")
def get_lectures(db: Session = Depends(get_db)):
    lectures = (
        db.query(Lecture).join(Instructor, Lecture.instructor_id == Instructor.id)
        .with_entities(Lecture.id, Lecture.name, Instructor.name.label("instructor_name"))
        .all()
    )
    # 리스트를 dict로 변환
    lecture_dicts = [
        {"id": lec.id, "name": lec.name, "instructor_name": lec.instructor_name}
        for lec in lectures
    ]
    return {"lectures": lecture_dicts}


@router.post("/enrollments", response_model=EnrollmentResponse, summary="수강신청")
def enroll(
        enrollment_in: EnrollmentRequest = Body(...),
        db: Session = Depends(get_db),
        student_uid: str = Depends(get_current_student_uid)
):
    """
    학생이 본인 토큰으로 수강신청을 요청합니다.
    이미 수강신청한 경우 409 에러를 반환합니다.
    """
    return enroll_student_in_lecture(db, student_uid, enrollment_in)

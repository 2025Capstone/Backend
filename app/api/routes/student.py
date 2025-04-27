from fastapi import APIRouter, Depends, Body
from app.services.auth_service import get_current_student
from sqlalchemy.orm import Session
from app.dependencies.db import get_db
from app.dependencies.auth import get_current_student_uid
from app.services.student import get_enrolled_lectures_for_student

router = APIRouter(
    dependencies=[Depends(get_current_student)]
)

@router.get("/lecture", summary="내 수강신청 강의 목록")
def get_my_enrolled_lectures(
    db: Session = Depends(get_db),
    student_uid: str = Depends(get_current_student_uid)
):
    """
    학생이 본인 토큰으로 수강신청한 강의 목록을 조회합니다.
    - 강의 id, 강의 이름, instructor 이름 반환
    """
    lectures = get_enrolled_lectures_for_student(db, student_uid)
    return {"lectures": lectures}

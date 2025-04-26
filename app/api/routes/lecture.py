from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.dependencies.db import get_db
from app.models.lecture import Lecture
from app.models.instructor import Instructor
from app.schemas.lecture import LectureListResponse, LectureBase
from app.services.auth_service import get_current_student

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

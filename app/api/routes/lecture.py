from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.dependencies.db import get_db
from app.models.lecture import Lecture
from app.schemas.lecture import LectureListResponse, LectureBase
from app.services.auth_service import get_current_student

router = APIRouter(
    dependencies=[Depends(get_current_student)]
)

@router.get("", response_model=LectureListResponse, description="강의 목록 조회")
def get_lectures(db: Session = Depends(get_db)):
    lectures = db.query(Lecture).all()
    return {"lectures": lectures}

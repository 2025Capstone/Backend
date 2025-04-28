from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.lecture import Lecture
from app.schemas.instructor import LectureCreate, LectureCreateResponse, MyLectureInfo

def create_lecture_for_instructor(db: Session, instructor_id: int, lecture_in: LectureCreate) -> LectureCreateResponse:
    # 중복 체크: 같은 instructor가 같은 이름의 강의를 이미 개설했는지 확인
    existing = db.query(Lecture).filter(
        Lecture.instructor_id == instructor_id,
        Lecture.name == lecture_in.name
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 동일한 이름의 강의를 개설하셨습니다.")

    lecture = Lecture(
        name=lecture_in.name,
        instructor_id=instructor_id
    )
    db.add(lecture)
    db.commit()
    db.refresh(lecture)
    return LectureCreateResponse(
        id=lecture.id,
        name=lecture.name,
        instructor_id=lecture.instructor_id,
        message="Lecture successfully created."
    )

def get_my_lectures(db: Session, instructor_id: int) -> list[MyLectureInfo]:
    lectures = db.query(Lecture).filter(Lecture.instructor_id == instructor_id).all()
    return [MyLectureInfo(id=lec.id, name=lec.name) for lec in lectures]

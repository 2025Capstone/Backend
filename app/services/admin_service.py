from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.lecture import Lecture
from app.schemas.instructor import LectureCreateResponse, AdminLectureCreate
from app.models.instructor import Instructor

def create_lecture_by_admin(db: Session, lecture_in: AdminLectureCreate) -> LectureCreateResponse:
    # instructor_id 유효성 체크
    instructor = db.query(Instructor).filter(Instructor.id == lecture_in.instructor_id).first()
    if not instructor:
        raise HTTPException(status_code=404, detail="지정한 instructor_id의 강사가 존재하지 않습니다.")

    # 중복 체크: 같은 instructor가 같은 이름의 강의를 이미 개설했는지 확인
    existing = db.query(Lecture).filter(
        Lecture.instructor_id == lecture_in.instructor_id,
        Lecture.name == lecture_in.name
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 동일한 이름의 강의를 개설하셨습니다.")

    lecture = Lecture(
        name=lecture_in.name,
        instructor_id=lecture_in.instructor_id,
        schedule=lecture_in.schedule,
        classroom=lecture_in.classroom,
        is_public=True
    )
    db.add(lecture)
    db.commit()
    db.refresh(lecture)
    return LectureCreateResponse(
        id=lecture.id,
        name=lecture.name,
        instructor_id=lecture.instructor_id,
        schedule=lecture.schedule,
        classroom=lecture.classroom,
        message="Lecture successfully created by admin."
    )

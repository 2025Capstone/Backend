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

def bulk_enroll_students_admin(db: Session, lecture_id: int, student_uid_list: list[str]) -> dict:
    from app.models.enrollment import Enrollment
    from app.models.student import Student
    enrolled = []
    already_enrolled = []
    not_found = []
    for uid in student_uid_list:
        student = db.query(Student).filter(Student.uid == uid).first()
        if not student:
            not_found.append(uid)
            continue
        exists = db.query(Enrollment).filter(Enrollment.student_uid == uid, Enrollment.lecture_id == lecture_id).first()
        if exists:
            already_enrolled.append(uid)
            continue
        enrollment = Enrollment(student_uid=uid, lecture_id=lecture_id)
        db.add(enrollment)
        enrolled.append(uid)
    db.commit()
    return {"enrolled": enrolled, "already_enrolled": already_enrolled, "not_found": not_found}

def get_all_lectures_with_instructor_name(db: Session):
    lectures = db.query(Lecture).join(Instructor).all()
    return [
        {
            "id": lec.id,
            "name": lec.name,
            "schedule": lec.schedule,
            "classroom": lec.classroom,
            "instructor_name": lec.instructor.name if lec.instructor else None
        } for lec in lectures
    ]

def bulk_unenroll_students_admin(db: Session, lecture_id: int, student_uid_list: list[str]) -> dict:
    from app.models.enrollment import Enrollment
    from app.models.student import Student
    unenrolled = []
    not_enrolled = []
    not_found = []
    for uid in student_uid_list:
        student = db.query(Student).filter(Student.uid == uid).first()
        if not student:
            not_found.append(uid)
            continue
        enrollment = db.query(Enrollment).filter(Enrollment.student_uid == uid, Enrollment.lecture_id == lecture_id).first()
        if not enrollment:
            not_enrolled.append(uid)
            continue
        db.delete(enrollment)
        unenrolled.append(uid)
    db.commit()
    return {"unenrolled": unenrolled, "not_enrolled": not_enrolled, "not_found": not_found}
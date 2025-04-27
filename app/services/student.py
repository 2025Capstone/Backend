from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import List
from app.models.enrollment import Enrollment
from app.models.lecture import Lecture
from app.models.instructor import Instructor
from app.schemas.student import EnrollmentRequest, EnrollmentResponse

class EnrolledLectureInfo:
    lecture_id: int
    lecture_name: str
    instructor_name: str

def enroll_student_in_lecture(db: Session, student_uid: str, enrollment_in: EnrollmentRequest) -> EnrollmentResponse:
    # 중복 체크: 이미 해당 학생이 해당 강의에 enrollment 되어 있는지 확인
    existing = db.query(Enrollment).filter(
        Enrollment.student_uid == student_uid,
        Enrollment.lecture_id == enrollment_in.lecture_id
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 해당 강의를 수강신청하셨습니다.")

    enrollment = Enrollment(
        student_uid=student_uid,
        lecture_id=enrollment_in.lecture_id
    )
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    return EnrollmentResponse(message="수강신청이 완료되었습니다.")

def get_enrolled_lectures_for_student(db: Session, student_uid: str) -> List[dict]:
    results = (
        db.query(
            Enrollment.lecture_id,
            Lecture.name.label('lecture_name'),
            Instructor.name.label('instructor_name')
        )
        .join(Lecture, Enrollment.lecture_id == Lecture.id)
        .join(Instructor, Lecture.instructor_id == Instructor.id)
        .filter(Enrollment.student_uid == student_uid)
        .all()
    )
    return [
        {
            "lecture_id": row.lecture_id,
            "lecture_name": row.lecture_name,
            "instructor_name": row.instructor_name
        }
        for row in results
    ]

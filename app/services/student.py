from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import List
from app.models.enrollment import Enrollment
from app.models.lecture import Lecture
from app.models.instructor import Instructor
from app.models.video import Video
from app.models.student import Student
from app.schemas.student import (
    EnrollmentRequest, EnrollmentResponse,
    EnrollmentCancelRequest, EnrollmentCancelResponse,
    LectureVideoListRequest, LectureVideoInfo,
    VideoLinkRequest, VideoLinkResponse,
    StudentProfileResponse,
    StudentNameUpdateRequest, StudentNameUpdateResponse
)

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

def get_lecture_videos_for_student(db: Session, student_uid: str, lecture_id: int) -> List[LectureVideoInfo]:
    # 1. 수강신청 여부 확인
    enrolled = db.query(Enrollment).filter(
        Enrollment.student_uid == student_uid,
        Enrollment.lecture_id == lecture_id
    ).first()
    if not enrolled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="해당 강의에 수강신청되어 있지 않습니다.")

    # 2. 영상 리스트 반환
    videos = db.query(Video).filter(Video.lecture_id == lecture_id).order_by(Video.index).all()
    return [
        LectureVideoInfo(
            id=video.id,
            index=video.index,
            title=video.title,
            duration=video.duration,
            upload_at=str(video.upload_at)
        ) for video in videos
    ]

def get_video_link_for_student(db: Session, student_uid: str, video_id: int) -> VideoLinkResponse:
    # 1. video 조회 및 존재 여부 확인
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="해당 영상이 존재하지 않습니다.")
    lecture_id = video.lecture_id
    # 2. 수강신청 여부 확인
    enrolled = db.query(Enrollment).filter(
        Enrollment.student_uid == student_uid,
        Enrollment.lecture_id == lecture_id
    ).first()
    if not enrolled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="해당 강의에 수강신청되어 있지 않습니다.")
    # 3. s3_link 반환
    return VideoLinkResponse(s3_link=video.s3_link)

def get_student_profile(db: Session, student_uid: str) -> StudentProfileResponse:
    student = db.query(Student).filter(Student.uid == student_uid).first()
    if not student:
        raise HTTPException(status_code=404, detail="학생 정보를 찾을 수 없습니다.")
    return StudentProfileResponse(email=student.email, name=student.name)

def update_student_name(db: Session, student_uid: str, name: str) -> StudentNameUpdateResponse:
    # 입력값 검증
    if not name or not name.strip():
        raise HTTPException(status_code=400, detail="이름을 입력해 주세요.")
    if len(name.strip()) > 255:
        raise HTTPException(status_code=400, detail="이름은 255자 이내여야 합니다.")

    student = db.query(Student).filter(Student.uid == student_uid).first()
    if not student:
        raise HTTPException(status_code=404, detail="학생 정보를 찾을 수 없습니다.")

    student.name = name.strip()
    db.commit()
    db.refresh(student)
    return StudentNameUpdateResponse(message="이름이 성공적으로 변경되었습니다.", name=student.name)

def cancel_enrollment(db: Session, student_uid: str, lecture_id: int) -> EnrollmentCancelResponse:
    enrollment = db.query(Enrollment).filter(
        Enrollment.student_uid == student_uid,
        Enrollment.lecture_id == lecture_id
    ).first()
    if not enrollment:
        raise HTTPException(status_code=404, detail="수강중인 강의가 아닙니다.")

    db.delete(enrollment)
    db.commit()
    return EnrollmentCancelResponse(message="수강이 성공적으로 취소되었습니다.")

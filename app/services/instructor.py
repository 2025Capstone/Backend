from sqlalchemy.orm import Session
from app.schemas.instructor import LectureCreate, LectureCreateResponse, MyLectureInfo, LectureStudentListRequest, LectureStudentInfo
from app.models.video import Video
from app.schemas.video import VideoResponse, VideoVisibilityUpdateRequest, VideoVisibilityUpdateResponse
from app.models.enrollment import Enrollment
from app.models.student import Student
from app.models.lecture import Lecture
from fastapi import HTTPException, status

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
        instructor_id=instructor_id,
        is_public=True  # 강의 개설 시 기본값을 공개(1)로 설정
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

def get_students_for_my_lecture(db: Session, instructor_id: int, lecture_id: int) -> list[LectureStudentInfo]:
    # 본인 강의인지 확인
    lecture = db.query(Lecture).filter(Lecture.id == lecture_id, Lecture.instructor_id == instructor_id).first()
    if not lecture:
        raise HTTPException(status_code=403, detail="본인이 개설한 강의가 아닙니다.")

    # 수강생 조회
    results = (
        db.query(Student.uid, Student.email, Student.name)
        .join(Enrollment, Enrollment.student_uid == Student.uid)
        .filter(Enrollment.lecture_id == lecture_id)
        .all()
    )
    return [LectureStudentInfo(uid=row.uid, email=row.email, name=row.name) for row in results]

def get_videos_for_my_lecture(db: Session, instructor_id: int, lecture_id: int) -> list[VideoResponse]:
    # 본인 강의인지 확인
    lecture = db.query(Lecture).filter(Lecture.id == lecture_id, Lecture.instructor_id == instructor_id).first()
    if not lecture:
        raise HTTPException(status_code=403, detail="본인이 개설한 강의가 아닙니다.")
    videos = db.query(Video).filter(Video.lecture_id == lecture_id).order_by(Video.index).all()
    # upload_at을 문자열로 변환하여 반환
    return [VideoResponse(
        id=video.id,
        lecture_id=video.lecture_id,
        title=video.title,
        s3_link=video.s3_link,
        duration=video.duration,
        index=video.index,
        upload_at=str(video.upload_at) if video.upload_at else None,
        is_public=video.is_public
    ) for video in videos]

def update_video_visibility(db: Session, instructor_id: int, req: VideoVisibilityUpdateRequest) -> VideoVisibilityUpdateResponse:
    # video 및 강의 소유권 확인
    video = db.query(Video).filter(Video.id == req.video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="해당 영상을 찾을 수 없습니다.")
    lecture = db.query(Lecture).filter(Lecture.id == video.lecture_id, Lecture.instructor_id == instructor_id).first()
    if not lecture:
        raise HTTPException(status_code=403, detail="본인이 개설한 강의의 영상만 수정할 수 있습니다.")
    video.is_public = req.is_public
    db.commit()
    db.refresh(video)
    return VideoVisibilityUpdateResponse(id=video.id, is_public=video.is_public, message="영상 공개여부가 변경되었습니다.")

def bulk_enroll_students(db: Session, instructor_id: int, lecture_id: int, student_uid_list: list[str]) -> dict:
    # 본인 강의인지 검증
    lecture = db.query(Lecture).filter(Lecture.id == lecture_id, Lecture.instructor_id == instructor_id).first()
    if not lecture:
        raise HTTPException(status_code=403, detail="본인이 개설한 강의가 아닙니다.")
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

def bulk_unenroll_students_for_instructor(db: Session, instructor_id: int, lecture_id: int, student_uid_list: list[str]) -> dict:
    # 본인 강의인지 검증
    lecture = db.query(Lecture).filter(Lecture.id == lecture_id, Lecture.instructor_id == instructor_id).first()
    if not lecture:
        raise HTTPException(status_code=403, detail="본인이 개설한 강의가 아닙니다.")
    unenrolled = []
    not_enrolled = []
    not_found = []
    for uid in student_uid_list:
        student = db.query(Student).filter(Student.uid == uid).first()
        if not student:
            not_found.append(uid)
            continue
        enrollment = db.query(Enrollment).filter(
            Enrollment.student_uid == uid,
            Enrollment.lecture_id == lecture_id
        ).first()
        if not enrollment:
            not_enrolled.append(uid)
            continue
        db.delete(enrollment)
        unenrolled.append(uid)
    db.commit()
    return {"unenrolled": unenrolled, "not_enrolled": not_enrolled, "not_found": not_found}

def get_unapproved_instructors(db: Session):
    """
    승인되지 않은(미승인) 강의자 리스트 반환
    """
    from app.models.instructor import Instructor
    return db.query(Instructor).filter(Instructor.is_approved == 0).all()

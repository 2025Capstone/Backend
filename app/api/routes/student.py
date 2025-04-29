from fastapi import APIRouter, Depends, Body

from app.models.instructor import Instructor
from app.models.lecture import Lecture
from app.schemas.lecture import LectureListResponse
from app.services.auth_service import get_current_student
from sqlalchemy.orm import Session
from app.dependencies.db import get_db
from app.dependencies.auth import get_current_student_uid
from app.services.student import (
    get_enrolled_lectures_for_student, get_lecture_videos_for_student, get_video_link_for_student, get_student_profile,
    update_student_name, cancel_enrollment, enroll_student_in_lecture
)
from app.schemas.student import (
    LectureVideoListRequest, LectureVideoListResponse,
    VideoLinkRequest, VideoLinkResponse,
    StudentProfileResponse,
    StudentNameUpdateRequest, StudentNameUpdateResponse,
    EnrollmentCancelRequest, EnrollmentCancelResponse, EnrollmentResponse, EnrollmentRequest
)

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

@router.post("/lecture/video", response_model=LectureVideoListResponse, summary="특정 강의의 영상 목록 조회")
def get_lecture_video_list(
    req: LectureVideoListRequest = Body(...),
    db: Session = Depends(get_db),
    student_uid: str = Depends(get_current_student_uid)
):
    """
    특정 강의의 영상 목록을 조회합니다. (수강신청 여부 확인)
    - 미수강자는 403 에러 반환
    - 성공 시 video 리스트 반환
    """
    videos = get_lecture_videos_for_student(db, student_uid, req.lecture_id)
    return LectureVideoListResponse(videos=videos)

@router.post("/lecture/video/link", response_model=VideoLinkResponse, summary="특정 영상의 S3 링크 제공")
def get_video_s3_link(
    req: VideoLinkRequest = Body(...),
    db: Session = Depends(get_db),
    student_uid: str = Depends(get_current_student_uid)
):
    """
    학생이 video id를 제공하면, 수강신청 여부 확인 후 해당 영상의 S3 링크를 반환합니다.
    - 미수강자는 403 에러 반환
    - 영상이 없으면 404 에러 반환
    """
    return get_video_link_for_student(db, student_uid, req.video_id)

@router.get("/profile", response_model=StudentProfileResponse, summary="내 프로필 정보 조회")
def get_my_profile(
    db: Session = Depends(get_db),
    student_uid: str = Depends(get_current_student_uid)
):
    """
    학생이 본인 토큰으로 자신의 email, 이름을 조회합니다.
    """
    return get_student_profile(db, student_uid)

@router.patch("/profile/name", response_model=StudentNameUpdateResponse, summary="학생 이름 변경")
def set_my_name(
    req: StudentNameUpdateRequest = Body(...),
    db: Session = Depends(get_db),
    student_uid: str = Depends(get_current_student_uid)
):
    """
    학생이 본인 이름을 설정(변경)합니다.
    - 이름이 비어있거나 255자 초과면 400 반환
    - 학생 정보가 없으면 404 반환
    """
    return update_student_name(db, student_uid, req.name)

@router.delete("/enrollments", response_model=EnrollmentCancelResponse, summary="수강 취소")
def cancel_my_enrollment(
    req: EnrollmentCancelRequest = Body(...),
    db: Session = Depends(get_db),
    student_uid: str = Depends(get_current_student_uid)
):
    """
    학생이 본인 토큰으로 수강중인 강의를 취소합니다.
    - 수강중이 아니면 404 반환
    """
    return cancel_enrollment(db, student_uid, req.lecture_id)

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

@router.get("", response_model=LectureListResponse, summary="강의 목록 조회")
def get_lectures(db: Session = Depends(get_db)):
    lectures = (
        db.query(Lecture)
        .join(Instructor, Lecture.instructor_id == Instructor.id)
        .filter(Lecture.is_public == True)
        .with_entities(Lecture.id, Lecture.name, Instructor.name.label("instructor_name"))
        .all()
    )
    # 리스트를 dict로 변환
    lecture_dicts = [
        {"id": lec.id, "name": lec.name, "instructor_name": lec.instructor_name}
        for lec in lectures
    ]
    return {"lectures": lecture_dicts}

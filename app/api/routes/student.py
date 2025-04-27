from fastapi import APIRouter, Depends, Body
from app.services.auth_service import get_current_student
from sqlalchemy.orm import Session
from app.dependencies.db import get_db
from app.dependencies.auth import get_current_student_uid
from app.services.student import get_enrolled_lectures_for_student, get_lecture_videos_for_student
from app.schemas.student import LectureVideoListRequest, LectureVideoListResponse

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

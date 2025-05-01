from fastapi import APIRouter, Depends, Body, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.dependencies.db import get_db
from app.dependencies.auth import get_current_instructor_id, get_current_instructor
from app.schemas.instructor import LectureCreate, LectureCreateResponse, MyLectureListResponse, LectureStudentListRequest, LectureStudentListResponse, BulkEnrollRequest, BulkEnrollResponse
from app.schemas.lecture import LectureVisibilityUpdateRequest, LectureVisibilityUpdateResponse
from app.schemas.video import VideoResponse, VideoVisibilityUpdateRequest, VideoVisibilityUpdateResponse, VideoCreate
from app.services.instructor import create_lecture_for_instructor, get_my_lectures, get_students_for_my_lecture, get_videos_for_my_lecture, update_video_visibility, bulk_enroll_students
from app.services.video_service import upload_video_to_s3
from app.models.lecture import Lecture
from app.models.video import Video
from app.utils.video_helpers import extract_video_duration

router = APIRouter(
    dependencies=[Depends(get_current_instructor)]
)


@router.get("/lectures", response_model=MyLectureListResponse, summary="내 강의 목록 조회")
def get_my_lecture_list(
    db: Session = Depends(get_db),
    instructor_id: int = Depends(get_current_instructor_id)
):
    """
    강의자가 본인 토큰으로 자신의 강의 목록을 조회합니다.
    """
    lectures = get_my_lectures(db, instructor_id)
    return MyLectureListResponse(lectures=lectures)

@router.post("/lecture/students", response_model=LectureStudentListResponse, summary="내 강의 수강생 목록 조회")
def get_my_lecture_students(
    req: LectureStudentListRequest = Body(...),
    db: Session = Depends(get_db),
    instructor_id: int = Depends(get_current_instructor_id)
):
    """
    강의자가 본인 강의의 수강생 목록을 조회합니다.
    - 본인 강의가 아니면 403 반환
    """
    students = get_students_for_my_lecture(db, instructor_id, req.lecture_id)
    return LectureStudentListResponse(students=students)

@router.get("/lecture/videos", response_model=list[VideoResponse], summary="내 강의 영상 목록 조회")
def get_my_lecture_videos(
    lecture_id: int,
    db: Session = Depends(get_db),
    instructor_id: int = Depends(get_current_instructor_id)
):
    """
    강의자가 본인 토큰으로 자신의 강의에 속한 영상 전체 정보를 조회합니다.
    강의 id를 받아 본인 강의가 아니면 403 에러를 반환합니다.
    """
    return get_videos_for_my_lecture(db, instructor_id, lecture_id)

@router.patch("/lectures/visibility", response_model=LectureVisibilityUpdateResponse, summary="강의 공개여부 수정")
def update_lecture_visibility(
    req: LectureVisibilityUpdateRequest = Body(...),
    db: Session = Depends(get_db),
    instructor_id: int = Depends(get_current_instructor_id)
):
    """
    강의자가 본인 소유의 강의의 공개/비공개 여부를 수정합니다.
    """
    lecture = db.query(Lecture).filter(Lecture.id == req.lecture_id).first()
    if not lecture:
        raise HTTPException(status_code=404, detail="해당 강의를 찾을 수 없습니다.")
    if lecture.instructor_id != instructor_id:
        raise HTTPException(status_code=403, detail="본인 소유의 강의만 수정할 수 있습니다.")
    lecture.is_public = req.is_public
    db.commit()
    db.refresh(lecture)
    return LectureVisibilityUpdateResponse(
        id=lecture.id,
        is_public=lecture.is_public,
        message="공개여부가 성공적으로 변경되었습니다."
    )

@router.patch("/lecture/video/visibility", response_model=VideoVisibilityUpdateResponse, summary="내 강의 영상 공개여부 수정")
def update_my_video_visibility(
    req: VideoVisibilityUpdateRequest = Body(...),
    db: Session = Depends(get_db),
    instructor_id: int = Depends(get_current_instructor_id)
):
    """
    강의자가 본인 강의의 영상 공개여부를 수정합니다.
    - video_id로 식별하며, 본인 강의가 아니면 403 반환
    """
    return update_video_visibility(db, instructor_id, req)

@router.post("/upload-video", response_model=VideoResponse, summary="비디오 업로드")
def upload_video(
        video_data: VideoCreate = Depends(VideoCreate.as_form),
        file: UploadFile = File(...),
        db: Session = Depends(get_db),
        instructor_id: int = Depends(get_current_instructor_id)
):
    """
    강의 영상 업로드 API (instructor)
    - 파일 형식 검증: video/*
    - moviepy를 이용하여 영상 길이(duration) 추출
    - 해당 강의의 기존 영상 개수를 기반으로 영상 순서(index) 결정
    - AWS S3에 영상 업로드 후, S3 링크(s3_link) 획득
    - DB에 Video 레코드 생성 후 응답 반환
    - 강의자가 본인 강의에만 업로드할 수 있도록 검증
    """
    lecture = db.query(Lecture).filter(Lecture.id == video_data.lecture_id, Lecture.instructor_id == instructor_id).first()
    if not lecture:
        raise HTTPException(status_code=403, detail="본인이 개설한 강의에만 영상을 업로드할 수 있습니다.")

    if not file.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="비디오 파일만 업로드 가능합니다.")

    try:
        duration = extract_video_duration(file)
        video_count = db.query(Video).filter(Video.lecture_id == video_data.lecture_id).count()
        video_index = video_count + 1
        s3_link, unique_folder = upload_video_to_s3(file.file, file.filename)
        new_video = Video(
            lecture_id=video_data.lecture_id,
            title=video_data.title,
            s3_link=s3_link,
            duration=int(duration),
            index=video_index,
            is_public=1
        )
        db.add(new_video)
        db.commit()
        db.refresh(new_video)
        return VideoResponse(
            id=new_video.id,
            lecture_id=new_video.lecture_id,
            title=new_video.title,
            s3_link=new_video.s3_link,
            duration=new_video.duration,
            index=new_video.index,
            upload_at=str(new_video.upload_at) if new_video.upload_at else None,
            is_public=new_video.is_public
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/lecture/bulk-enroll", response_model=BulkEnrollResponse, summary="여러 학생 일괄 수강신청")
def bulk_enroll_students_api(
    req: BulkEnrollRequest = Body(...),
    db: Session = Depends(get_db),
    instructor_id: int = Depends(get_current_instructor_id)
):
    """
    강의자가 여러 학생을 한 번에 수강신청시킴 (이미 수강신청된 학생은 건너뜀)
    """
    result = bulk_enroll_students(db, req.lecture_id, req.student_uid_list)
    return BulkEnrollResponse(**result)
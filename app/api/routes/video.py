from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from app.services.video_service import upload_video_to_s3
from sqlalchemy.orm import Session
from app.models.video import Video
from app.schemas.video import VideoResponse, VideoCreate
from app.utils.video_helpers import extract_video_duration  # 위 helper 함수 위치에 따라 import
from app.dependencies.db import get_db
from app.dependencies.firebase_deps import get_verified_firebase_user

router = APIRouter(
    dependencies=[Depends(get_verified_firebase_user)]
)

@router.post("/upload", response_model=VideoResponse)
def upload_video(
        video_data: VideoCreate = Depends(VideoCreate.as_form),  # 스키마를 통해 요청 데이터 검증
        file: UploadFile = File(...),
        db: Session = Depends(get_db)
):
    """
    강의 영상 업로드 API
    - 파일 형식 검증: video/*
    - moviepy를 이용하여 영상 길이(duration) 추출
    - 해당 강의의 기존 영상 개수를 기반으로 영상 순서(index) 결정
    - AWS S3에 영상 업로드 후, S3 링크(s3_link) 획득
    - DB에 Video 레코드 생성 후 응답 반환
    """
    if not file.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="비디오 파일만 업로드 가능합니다.")

    try:
        # 1. 영상 길이 추출
        duration = extract_video_duration(file)

        # 2. 같은 강의 내 영상 순서(index) 결정
        video_count = db.query(Video).filter(Video.lecture_id == video_data.lecture_id).count()
        video_index = video_count + 1

        # 3. S3에 업로드하여 영상 링크 획득
        s3_link, unique_folder = upload_video_to_s3(file.file, file.filename)  # 튜플을 개별 변수로 할당
        # 4. Video 레코드 생성
        new_video = Video(
            lecture_id=video_data.lecture_id,
            title=video_data.title,
            s3_link=s3_link,
            duration=int(duration),
            index=video_index
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
            index=new_video.index
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
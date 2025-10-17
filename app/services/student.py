from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import List
from app.models.enrollment import Enrollment
from app.models.lecture import Lecture
from app.models.instructor import Instructor
from app.models.video import Video
from app.models.student import Student
from app.models.watch_history import WatchHistory
from app.models.drowsiness_level import DrowsinessLevel
from app.schemas.student import (
    EnrollmentRequest, EnrollmentResponse,
    EnrollmentCancelRequest, EnrollmentCancelResponse,
    LectureVideoListRequest, LectureVideoInfo,
    VideoLinkRequest, VideoLinkResponse,
    StudentProfileResponse,
    StudentNameUpdateRequest, StudentNameUpdateResponse
)

import boto3
from botocore.exceptions import NoCredentialsError
from app.core.config import settings
from uuid import uuid4
from fastapi import UploadFile
import os
import io

s3_client = boto3.client(
    "s3",
    aws_access_key_id=settings.AWS_ACCESS_KEY,
    aws_secret_access_key=settings.AWS_SECRET_KEY,
    region_name=settings.AWS_REGION
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
            Instructor.name.label('instructor_name'),
            Lecture.classroom,
            Lecture.schedule
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
            "instructor_name": row.instructor_name,
            "classroom": row.classroom,
            "schedule": row.schedule
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

    # 2. 영상 리스트 반환 (공개 영상만)
    videos = db.query(Video).filter(Video.lecture_id == lecture_id, Video.is_public == 1).order_by(Video.index).all()
    video_ids = [v.id for v in videos]
    # 3. 학생별 시청 진척도 조회
    watch_histories = db.query(WatchHistory).filter(
        WatchHistory.student_uid == student_uid,
        WatchHistory.video_id.in_(video_ids)
    ).all()
    percent_map = {h.video_id: h.watched_percent for h in watch_histories}
    return [
        LectureVideoInfo(
            id=video.id,
            index=video.index,
            title=video.title,
            duration=video.duration,
            upload_at=str(video.upload_at),
            watched_percent=percent_map.get(video.id, 0)
        ) for video in videos
    ]

def get_video_link_for_student(db: Session, student_uid: str, video_id: int) -> VideoLinkResponse:
    # 1. video 조회 및 존재 여부 확인
    video = db.query(Video).filter(Video.id == video_id, Video.is_public == 1).first()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="해당 영상이 존재하지 않거나 비공개 상태입니다.")
    lecture_id = video.lecture_id
    # 2. 수강신청 여부 확인
    enrolled = db.query(Enrollment).filter(
        Enrollment.student_uid == student_uid,
        Enrollment.lecture_id == lecture_id
    ).first()
    if not enrolled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="해당 강의에 수강신청되어 있지 않습니다.")
    # 3. 시청 진척도 조회
    history = db.query(WatchHistory).filter(
        WatchHistory.student_uid == student_uid,
        WatchHistory.video_id == video_id
    ).first()
    watched_percent = history.watched_percent if history else 0
    # 4. 졸음 정도 조회 (timestamp 순서대로 정렬)
    drowsiness_records = db.query(DrowsinessLevel).filter(
        DrowsinessLevel.video_id == video_id,
        DrowsinessLevel.student_uid == student_uid
    ).order_by(DrowsinessLevel.timestamp.asc()).all()
    
    # 디버깅: 조회된 레코드 수 로그
    print(f"[get_video_link_for_student] video_id={video_id}, student_uid={student_uid}")
    print(f"[get_video_link_for_student] 조회된 졸음 레코드 수: {len(drowsiness_records)}")
    if drowsiness_records:
        print(f"[get_video_link_for_student] 첫 번째 레코드: timestamp={drowsiness_records[0].timestamp}, score={drowsiness_records[0].drowsiness_score}")
    
    # 졸음 데이터를 { t: 시간(초), value: 졸음점수 } 형식으로 변환
    # DB의 timestamp는 분 단위 (0, 2, 4, ...) → 초 단위로 변환 (0, 120, 240, ...)
    drowsiness_levels = [
        {"t": record.timestamp * 60, "value": record.drowsiness_score}
        for record in drowsiness_records
    ]
    
    print(f"[get_video_link_for_student] 변환된 drowsiness_levels: {drowsiness_levels}")
    
    # 5. s3_link, watched_percent, drowsiness_levels 반환
    return VideoLinkResponse(s3_link=video.s3_link, watched_percent=watched_percent, drowsiness_levels=drowsiness_levels)

def get_student_profile(db: Session, student_uid: str) -> StudentProfileResponse:
    student = db.query(Student).filter(Student.uid == student_uid).first()
    if not student:
        raise HTTPException(status_code=404, detail="학생 정보를 찾을 수 없습니다.")
    return StudentProfileResponse(
        email=student.email,
        name=student.name,
        profile_image_url=student.profile_image_url
    )

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

def upload_profile_image_to_s3(file: UploadFile) -> str:
    """
    멀티파트로 받은 이미지를 S3의 /profile_image/ 폴더에 업로드하고, S3 URL을 반환합니다.
    """
    try:
        ext = os.path.splitext(file.filename)[1]
        unique_name = f"{uuid4().hex}{ext}"
        s3_key = f"profile_image/{unique_name}"
        s3_client.upload_fileobj(
            file.file,
            settings.AWS_S3_BUCKET_NAME,
            s3_key,
            ExtraArgs={"ContentType": file.content_type}
        )
        s3_url = f"https://{settings.AWS_S3_BUCKET_NAME}.s3.{settings.AWS_REGION}.amazonaws.com/{s3_key}"
        return s3_url
    except NoCredentialsError:
        raise HTTPException(status_code=500, detail="S3 인증 정보가 없습니다.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"프로필 이미지 업로드 실패: {str(e)}")

def upload_video_image_to_s3(image_file: bytes, ext: str) -> str:
    """
    영상 썸네일 이미지를 S3의 /video_image/ 폴더에 업로드하고, S3 URL을 반환합니다.
    """
    try:
        unique_name = f"{uuid4().hex}{ext}"
        s3_key = f"video_image/{unique_name}"
        s3_client.upload_fileobj(
            io.BytesIO(image_file),
            settings.AWS_S3_BUCKET_NAME,
            s3_key,
            ExtraArgs={"ContentType": f"image/{ext.lstrip('.')}"}
        )
        s3_url = f"https://{settings.AWS_S3_BUCKET_NAME}.s3.{settings.AWS_REGION}.amazonaws.com/{s3_key}"
        return s3_url
    except NoCredentialsError:
        raise HTTPException(status_code=500, detail="S3 인증 정보가 없습니다.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"비디오 이미지 업로드 실패: {str(e)}")

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

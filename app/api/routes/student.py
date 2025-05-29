import glob
import time

from fastapi import APIRouter, Depends, Body, UploadFile, File, WebSocket, WebSocketDisconnect
from uuid import uuid4
import os
import numpy as np
import torch
from app.schemas.drowsiness import (
    DrowsinessStartRequest, DrowsinessStartResponse,
    DrowsinessVerifyRequest, DrowsinessVerifyResponse,
    DrowsinessFinishRequest, DrowsinessFinishResponse, DrowsinessPrediction
)
from app.ml.pipeline import MultimodalFatigueModel
from app.ml.face_GNN import FaceSTGCNModel
from app.ml.hrv_embedding import HRVFeatureEmbedder
# from app.ml.data_loader import ... # 실제 CSV 파싱 필요시
# from app.ml import ... # edge_index 등 필요시 import

from fastapi.exceptions import HTTPException
from sqlalchemy import func
from app.models.instructor import Instructor
from app.models.lecture import Lecture
from app.models.video import Video
from app.models.enrollment import Enrollment
from app.models.watch_history import WatchHistory
from app.models.student import Student
from app.schemas.lecture import LectureListResponse
from app.schemas.student import (
    LectureVideoListRequest, LectureVideoListResponse,
    VideoLinkRequest, VideoLinkResponse,
    StudentProfileResponse,
    StudentNameUpdateRequest, StudentNameUpdateResponse,
    EnrollmentCancelRequest, EnrollmentCancelResponse, EnrollmentResponse, EnrollmentRequest,
    VideoProgressUpdateRequest, VideoProgressUpdateResponse
)
from app.services.auth_service import get_current_student
from app.services.student import (
    get_enrolled_lectures_for_student, get_lecture_videos_for_student, get_video_link_for_student, get_student_profile,
    update_student_name, cancel_enrollment, enroll_student_in_lecture, upload_profile_image_to_s3
)
from sqlalchemy.orm import Session
from app.dependencies.db import get_db
from app.dependencies.auth import get_current_student_uid

router = APIRouter(
    dependencies=[Depends(get_current_student)]
)

@router.get("/lecture", summary="내 수강신청 강의 목록")
def get_my_enrolled_lectures(
    db: Session = Depends(get_db),
    student_uid: str = Depends(get_current_student_uid)
):
    """
    학생이 본인 토큰으로 수강신청된 강의 목록을 조회합니다.
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

@router.post("/lecture/video/progress", response_model=VideoProgressUpdateResponse, summary="영상 진척도 기록")
def update_video_progress(
    req: VideoProgressUpdateRequest = Body(...),
    db: Session = Depends(get_db),
    student_uid: str = Depends(get_current_student_uid)
):
    # 1. 영상 조회
    video = db.query(Video).filter(Video.id == req.video_id, Video.is_public == 1).first()
    if not video:
        raise HTTPException(status_code=404, detail="해당 영상이 존재하지 않거나 비공개 상태입니다.")
    # 2. 수강신청 여부 확인
    enrollment = db.query(Enrollment).filter(
        Enrollment.student_uid == student_uid,
        Enrollment.lecture_id == video.lecture_id
    ).first()
    if not enrollment:
        raise HTTPException(status_code=403, detail="해당 강의에 수강신청되어 있지 않습니다.")
    # 3. 진척도 기록 (upsert)
    history = db.query(WatchHistory).filter(
        WatchHistory.student_uid == student_uid,
        WatchHistory.video_id == req.video_id
    ).first()
    if history:
        history.timestamp = func.now()
        history.watched_percent = max(getattr(history, 'watched_percent', 0), req.watched_percent)
    else:
        history = WatchHistory(
            student_uid=student_uid,
            video_id=req.video_id,
            timestamp=func.now(),
            watched_percent=req.watched_percent
        )
        db.add(history)
    db.commit()
    return VideoProgressUpdateResponse(message="진척도가 저장되었습니다.")

@router.post("/profile/image", summary="프로필 사진 업로드 및 저장")
def upload_my_profile_image(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    student_uid: str = Depends(get_current_student_uid)
):
    """
    학생이 본인 프로필 사진을 업로드하면 S3에 저장 후, 해당 URL을 DB에 저장합니다.
    """
    s3_url = upload_profile_image_to_s3(file)
    # DB에 저장
    student = db.query(Student).filter(Student.uid == student_uid).first()
    if not student:
        raise HTTPException(status_code=404, detail="학생 정보를 찾을 수 없습니다.")
    student.profile_image_url = s3_url
    db.commit()
    db.refresh(student)
    return {"profile_image_url": s3_url}

@router.get("/recent-incomplete-videos", summary="최근 시청기록 중 미완료 영상 10개 조회")
def get_recent_incomplete_videos(
    db: Session = Depends(get_db),
    student_uid: str = Depends(get_current_student_uid)
):
    """
    시청 완료하지 않은(95% 미만) 영상 중 최근 10개를 반환합니다.
    - video_id, lecture_id, lecture_name, video_name, instructor_name, timestamp 반환
    """
    results = (
        db.query(
            WatchHistory.video_id,
            Video.lecture_id,
            Lecture.name.label("lecture_name"),
            Video.title.label("video_name"),
            Instructor.name.label("instructor_name"),
            WatchHistory.timestamp,
            Video.video_image_url
        )
        .join(Video, WatchHistory.video_id == Video.id)
        .join(Lecture, Video.lecture_id == Lecture.id)
        .join(Instructor, Lecture.instructor_id == Instructor.id)
        .filter(WatchHistory.student_uid == student_uid)
        .filter(WatchHistory.watched_percent < 95)
        .order_by(WatchHistory.timestamp.desc())
        .limit(10)
        .all()
    )
    return [
        {
            "video_id": row.video_id,
            "lecture_id": row.lecture_id,
            "lecture_name": row.lecture_name,
            "video_name": row.video_name,
            "instructor_name": row.instructor_name,
            "timestamp": row.timestamp,
            "video_image_url": row.video_image_url
        }
        for row in results
    ]

# =========================
# 졸음 탐지 플로우 API
# =========================

import pandas as pd

from sqlalchemy.orm import Session as DBSession
from fastapi import Depends
from app.dependencies.db import get_db



import random

from app.models.drowsiness_session import DrowsinessSession

@router.post("/drowsiness/start", response_model=DrowsinessStartResponse, summary="졸음 탐지 세션 시작")
def start_drowsiness_detection(
    req: DrowsinessStartRequest = Body(...),
    db: Session = Depends(get_db),
    student_uid: str = Depends(get_current_student_uid)
):
    """
    졸음 탐지 세션을 시작하고, 6자리 인증코드를 생성하여 클라이언트에 반환합니다.
    클라이언트는 이 코드를 웨어러블 디바이스에 입력해야 합니다.
    """
    session_id = str(uuid4())
    auth_code = f"{random.randint(0, 999999):06d}"
    # DB에 세션 생성
    session_obj = DrowsinessSession(
        session_id=session_id,
        student_uid=student_uid,
        video_id=req.video_id,
        auth_code=auth_code,
        verified=False
    )
    db.add(session_obj)
    db.commit()
    return DrowsinessStartResponse(session_id=session_id, message=f"세션이 시작되었습니다. 인증코드: {auth_code}")

@router.post("/drowsiness/verify", response_model=DrowsinessVerifyResponse, summary="웨어러블 인증코드 검증")
def verify_drowsiness_wearable(
    req: DrowsinessVerifyRequest = Body(...),
    db: Session = Depends(get_db),
    student_uid: str = Depends(get_current_student_uid)
):
    """
    웨어러블에서 입력한 인증코드를 검증합니다. (클라이언트와 웨어러블이 동일한 코드를 입력해야 연동 성공)
    """
    session_obj = db.query(DrowsinessSession).filter_by(session_id=req.session_id).first()
    if not session_obj or session_obj.student_uid != student_uid:
        raise HTTPException(status_code=404, detail="세션이 존재하지 않습니다.")
    if req.code != session_obj.auth_code:
        return DrowsinessVerifyResponse(session_id=req.session_id, verified=False, message="인증코드가 일치하지 않습니다.")
    session_obj.verified = True
    db.commit()
    return DrowsinessVerifyResponse(session_id=req.session_id, verified=True, message="웨어러블 연동이 완료되었습니다.")

from app.utils.drowsiness_data_utils import make_shard_and_pt
from app.ml.data_loader import SessionSequenceDataset

@router.post("/drowsiness/finish", response_model=DrowsinessFinishResponse)
def finish_drowsiness_detection(
    req: DrowsinessFinishRequest,
    db: Session = Depends(get_db),
    student_uid: str = Depends(get_current_student_uid)
):
    import torch
    session_id = req.session_id
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../drowsiness_data'))
    session_dir = os.path.join(base_dir, session_id)
    if not os.path.isdir(session_dir):
        raise HTTPException(status_code=404, detail="Landmark 데이터 디렉토리가 존재하지 않습니다.")
    csv_files = glob.glob(os.path.join(session_dir, '*.csv'))
    if not csv_files:
        raise HTTPException(status_code=404, detail="Landmark 데이터 CSV 파일이 존재하지 않습니다.")

    timeout, interval, waited = 120, 1, 0
    while waited < timeout:
        last_modified = max(os.path.getmtime(f) for f in csv_files)
        elapsed = time.time() - last_modified
        if elapsed >= 2:
            break
        print(f"Landmark 데이터 저장 중... (경과 {elapsed:.2f}s)")
        time.sleep(interval)
        waited += interval
    else:
        raise HTTPException(status_code=500, detail="Landmark 데이터 저장 대기 타임아웃.")

    try:
        pt_path = make_shard_and_pt(session_id, base_dir=base_dir, shard_size=150)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Landmark 데이터 병합/pt 변환 실패: {e}")

    if pt_path and os.path.exists(pt_path):
        try:
            pt_data = torch.load(pt_path)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"PT 파일 로드 실패: {e}")
    else:
        raise HTTPException(status_code=404, detail="PT 파일이 존재하지 않습니다.")

    edge_index_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../ml/edge_index_core.pt'))
    try:
        edge_index = torch.load(edge_index_path, map_location='cpu')
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"edge_index 로드 실패: {e}")

    try:
        SEQ_LEN, STRIDE = 12, 3
        dataset = SessionSequenceDataset(session_dir, seq_len=SEQ_LEN, stride=STRIDE)
        if len(dataset) == 0:
            raise HTTPException(status_code=400, detail="1분 이상 시청하지 않아 분석이 불가능합니다.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"데이터셋 로딩 실패: {e}")

    try:
        model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../ml/best_model.pt'))
        model = MultimodalFatigueModel(num_classes=5)

        # ✅ state_dict 추출 및 로드
        checkpoint = torch.load(model_path, map_location='cpu')
        if 'model' in checkpoint:
            model.load_state_dict(checkpoint['model'])
        else:
            model.load_state_dict(checkpoint)
        model.eval()

        all_preds, all_mins = [], []
        with torch.no_grad():
            for idx in range(len(dataset)):
                face, wear, _ = dataset[idx]
                face = face.unsqueeze(0)
                wear = wear.unsqueeze(0)
                pred, aux = model(face, wear, edge_index)

                # ✅ pred는 회귀값, conf는 1.0
                lvl = float(pred.item())
                conf = 1.0

                all_preds.append(lvl)
                all_mins.append(idx)


    except Exception as e:
        raise HTTPException(status_code=500, detail=f"모델 예측 실패: {e}")

    # === 졸음 수준 DB 저장 ===
    from app.models.drowsiness_session import DrowsinessSession
    from app.models.drowsiness_level import DrowsinessLevel

    # session_id로 세션 정보 조회
    session_obj = db.query(DrowsinessSession).filter_by(session_id=session_id).first()
    if not session_obj:
        raise HTTPException(status_code=404, detail="세션 정보를 찾을 수 없습니다.")
    if session_obj.student_uid != student_uid:
        raise HTTPException(status_code=403, detail="본인 세션이 아닙니다.")
    video_id = session_obj.video_id

    # 기존 데이터 삭제
    db.query(DrowsinessLevel).filter_by(video_id=video_id, student_uid=student_uid).delete()
    db.commit()

    db.add_all([
        DrowsinessLevel(
            video_id=video_id,
            student_uid=student_uid,
            timestamp=i,
            drowsiness_score=score
        ) for i, score in enumerate(all_preds)
    ])
    db.commit()


    prediction = DrowsinessPrediction(
        session_id=session_id,
        drowsiness_level=all_preds[-1],
        confidence=conf,  # 마지막 conf=1.0
        details={"minute": all_mins[-1], "all_preds": all_preds}
    )
    return DrowsinessFinishResponse(
        session_id=session_id,
        prediction=prediction,
        message="졸음 예측이 완료되었습니다. (모든 1분 단위 예측)"
    )
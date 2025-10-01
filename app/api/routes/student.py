import glob
import time
import uuid
import random
import os

# --- FastAPI ---
from fastapi import APIRouter, Depends, Body, UploadFile, File, HTTPException

# --- 데이터베이스 및 인증 ---
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.dependencies.db import get_db
from app.dependencies.auth import get_current_student_uid
from app.services.auth_service import get_current_student

# --- Firebase Admin SDK ---
import firebase_admin

# --- 스키마 (Schemas) ---
from app.schemas.drowsiness import (
    DrowsinessStartRequest, DrowsinessStartResponse,
    DrowsinessVerifyRequest, DrowsinessVerifyResponse,
    DrowsinessFinishRequest, DrowsinessFinishResponse, DrowsinessPrediction
)
from app.schemas.lecture import LectureListResponse
from app.schemas.student import (
    LectureVideoListRequest, LectureVideoListResponse,
    VideoLinkRequest, VideoLinkResponse,
    StudentProfileResponse,
    StudentNameUpdateRequest, StudentNameUpdateResponse,
    EnrollmentCancelRequest, EnrollmentCancelResponse, EnrollmentResponse, EnrollmentRequest,
    VideoProgressUpdateRequest, VideoProgressUpdateResponse
)

# --- 모델 (Database Models) ---
from app.models.instructor import Instructor
from app.models.lecture import Lecture
from app.models.video import Video
from app.models.enrollment import Enrollment
from app.models.watch_history import WatchHistory
from app.models.student import Student

# --- 서비스 (Business Logic) ---
from app.services.student import (
    get_enrolled_lectures_for_student, get_lecture_videos_for_student, get_video_link_for_student, get_student_profile,
    update_student_name, cancel_enrollment, enroll_student_in_lecture, upload_profile_image_to_s3
)

# --- 머신러닝 및 데이터 처리 ---
import pandas as pd
import torch
from app.utils.drowsiness_data_utils import make_shard_and_pt
from app.ml.data_loader import SessionSequenceDataset
from app.ml.pipeline import MultimodalFatigueModel

# APIRouter에서 전역 dependencies 제거
router = APIRouter()


# =========================
# 학생 강의 관련 API (개별 인증 추가)
# =========================

@router.get("/lecture", summary="내 수강신청 강의 목록", dependencies=[Depends(get_current_student)])
def get_my_enrolled_lectures(
        db: Session = Depends(get_db),
        student_uid: str = Depends(get_current_student_uid)
):
    lectures = get_enrolled_lectures_for_student(db, student_uid)
    return {"lectures": lectures}


@router.post("/lecture/video", response_model=LectureVideoListResponse, summary="특정 강의의 영상 목록 조회",
             dependencies=[Depends(get_current_student)])
def get_lecture_video_list(
        req: LectureVideoListRequest = Body(...),
        db: Session = Depends(get_db),
        student_uid: str = Depends(get_current_student_uid)
):
    videos = get_lecture_videos_for_student(db, student_uid, req.lecture_id)
    return LectureVideoListResponse(videos=videos)


@router.post("/lecture/video/link", response_model=VideoLinkResponse, summary="특정 영상의 S3 링크 제공",
             dependencies=[Depends(get_current_student)])
def get_video_s3_link(
        req: VideoLinkRequest = Body(...),
        db: Session = Depends(get_db),
        student_uid: str = Depends(get_current_student_uid)
):
    return get_video_link_for_student(db, student_uid, req.video_id)


@router.get("/profile", response_model=StudentProfileResponse, summary="내 프로필 정보 조회",
            dependencies=[Depends(get_current_student)])
def get_my_profile(
        db: Session = Depends(get_db),
        student_uid: str = Depends(get_current_student_uid)
):
    return get_student_profile(db, student_uid)


@router.patch("/profile/name", response_model=StudentNameUpdateResponse, summary="학생 이름 변경",
              dependencies=[Depends(get_current_student)])
def set_my_name(
        req: StudentNameUpdateRequest = Body(...),
        db: Session = Depends(get_db),
        student_uid: str = Depends(get_current_student_uid)
):
    return update_student_name(db, student_uid, req.name)


@router.post("/lecture/video/progress", response_model=VideoProgressUpdateResponse, summary="영상 진척도 기록",
             dependencies=[Depends(get_current_student)])
def update_video_progress(
        req: VideoProgressUpdateRequest = Body(...),
        db: Session = Depends(get_db),
        student_uid: str = Depends(get_current_student_uid)
):
    video = db.query(Video).filter(Video.id == req.video_id, Video.is_public == 1).first()
    if not video:
        raise HTTPException(status_code=404, detail="해당 영상이 존재하지 않거나 비공개 상태입니다.")
    enrollment = db.query(Enrollment).filter(
        Enrollment.student_uid == student_uid,
        Enrollment.lecture_id == video.lecture_id
    ).first()
    if not enrollment:
        raise HTTPException(status_code=403, detail="해당 강의에 수강신청되어 있지 않습니다.")
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


@router.post("/profile/image", summary="프로필 사진 업로드 및 저장", dependencies=[Depends(get_current_student)])
def upload_my_profile_image(
        file: UploadFile = File(...),
        db: Session = Depends(get_db),
        student_uid: str = Depends(get_current_student_uid)
):
    s3_url = upload_profile_image_to_s3(file)
    student = db.query(Student).filter(Student.uid == student_uid).first()
    if not student:
        raise HTTPException(status_code=404, detail="학생 정보를 찾을 수 없습니다.")
    student.profile_image_url = s3_url
    db.commit()
    db.refresh(student)
    return {"profile_image_url": s3_url}


@router.get("/recent-incomplete-videos", summary="최근 시청기록 중 미완료 영상 10개 조회", dependencies=[Depends(get_current_student)])
def get_recent_incomplete_videos(
        db: Session = Depends(get_db),
        student_uid: str = Depends(get_current_student_uid)
):
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

@router.post("/drowsiness/start", response_model=DrowsinessStartResponse, summary="졸음 탐지 세션 시작",
             dependencies=[Depends(get_current_student)])
def start_drowsiness_detection(
        req: DrowsinessStartRequest = Body(...),
        student_uid: str = Depends(get_current_student_uid)
):
    """
    졸음 탐지 세션을 시작하고, Firebase에 세션 데이터와 인덱스를 생성합니다.
    생성된 6자리 인증코드를 클라이언트에 반환합니다.
    """
    session_id = str(uuid.uuid4())
    auth_code = f"{random.randint(0, 999999):06d}"

    try:
        from firebase_admin import db

        ref = db.reference(f"{session_id}")
        ref.set({
            "pairing": {
                "paired": False,
                "stop": False,
                "auth_code": auth_code,
                "student_uid": student_uid,
                "video_id": req.video_id
            },
            "PPG_Data": {}
        })

        index_ref = db.reference(f"auth_code_index/{auth_code}")
        index_ref.set(session_id)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Firebase 세션 생성에 실패했습니다: {e}")

    return DrowsinessStartResponse(session_id=session_id, auth_code=auth_code,
                                   message="세션이 시작되었습니다. 웨어러블에 인증코드를 입력하세요.")


@router.post("/drowsiness/verify", response_model=DrowsinessVerifyResponse, summary="[웨어러블용] 인증코드로 검증")
def verify_drowsiness_from_wearable(
        req: DrowsinessVerifyRequest,
):
    """
    웨어러블 기기에서 전송한 인증코드를 기반으로 세션을 찾아 연동하고, 세션 ID를 반환합니다.
    이 API는 로그인 토큰이 필요 없습니다.
    """
    try:
        from firebase_admin import db

        index_ref = db.reference(f"auth_code_index/{req.code}")
        session_id = index_ref.get()

        if not session_id:
            raise HTTPException(status_code=404, detail="인증코드가 유효하지 않거나 만료되었습니다.")

        session_ref = db.reference(f"{session_id}/pairing")
        session_data = session_ref.get()

        if not session_data:
            raise HTTPException(status_code=404, detail="인덱스는 존재하지만, 해당 세션 데이터가 존재하지 않습니다.")

        session_ref.update({"paired": True})

        index_ref.delete()

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Firebase 데이터 검증/업데이트 중 오류가 발생했습니다: {e}")

    return DrowsinessVerifyResponse(session_id=session_id, verified=True, message="웨어러블 연동이 완료되었습니다.")


@router.post("/drowsiness/finish", response_model=DrowsinessFinishResponse, summary="졸음 탐지 세션 종료 및 분석",
             dependencies=[Depends(get_current_student)])
def finish_drowsiness_detection(
        req: DrowsinessFinishRequest,
        student_uid: str = Depends(get_current_student_uid)
):
    session_id = req.session_id

    from firebase_admin import db

    try:
        session_ref = db.reference(f"{session_id}")
        pairing_ref = session_ref.child("pairing")
        pairing_data = pairing_ref.get()
        if not pairing_data:
            raise HTTPException(status_code=404, detail="세션 정보를 찾을 수 없습니다.")
        if pairing_data.get("student_uid") != student_uid:
            raise HTTPException(status_code=403, detail="본인의 세션이 아닙니다.")
        pairing_ref.update({"stop": True})
        video_id = pairing_data.get("video_id")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Firebase 세션 종료 처리 중 오류 발생: {e}")

    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../drowsiness_data'))
    session_dir = os.path.join(base_dir, session_id)

    try:
        ppg_data_ref = session_ref.child("PPG_Data")
        ppg_data = ppg_data_ref.get()
        if ppg_data:
            ppg_list = [v for k, v in ppg_data.items()]
            df = pd.DataFrame(ppg_list)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values(by='timestamp').reset_index(drop=True)
            os.makedirs(session_dir, exist_ok=True)
            ppg_csv_path = os.path.join(session_dir, 'ppg_data.csv')
            df.to_csv(ppg_csv_path, index=False)
        else:
            print(f"Warning: 세션 {session_id}에 대한 PPG 데이터가 없습니다.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Firebase PPG 데이터 처리 실패: {e}")

    if not os.path.isdir(session_dir):
        raise HTTPException(status_code=404, detail="Landmark 데이터 디렉토리가 존재하지 않습니다.")
    csv_files = glob.glob(os.path.join(session_dir, '*.csv'))
    if not csv_files:
        raise HTTPException(status_code=404, detail="Landmark 데이터 CSV 파일이 존재하지 않습니다.")

    timeout, interval, waited = 120, 1, 0
    while waited < timeout:
        last_modified = max(os.path.getmtime(f) for f in csv_files)
        if time.time() - last_modified >= 2: break
        time.sleep(interval)
        waited += interval
    else:
        raise HTTPException(status_code=500, detail="Landmark 데이터 저장 대기 타임아웃.")

    try:
        pt_path = make_shard_and_pt(session_id, base_dir=base_dir, shard_size=150)
        if not (pt_path and os.path.exists(pt_path)):
            raise FileNotFoundError("PT 파일이 생성되지 않았습니다.")
        SEQ_LEN, STRIDE = 12, 3
        dataset = SessionSequenceDataset(session_dir, seq_len=SEQ_LEN, stride=STRIDE)
        if len(dataset) == 0:
            raise ValueError("1분 이상 시청하지 않아 분석이 불가능합니다.")
        edge_index_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../ml/edge_index_core.pt'))
        edge_index = torch.load(edge_index_path, map_location='cpu')
        model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../ml/best_model.pt'))
        model = MultimodalFatigueModel(num_classes=5)
        checkpoint = torch.load(model_path, map_location='cpu')
        model.load_state_dict(checkpoint.get('model', checkpoint))
        model.eval()
        all_preds, all_mins = [], []
        with torch.no_grad():
            for idx in range(len(dataset)):
                face, wear, _ = dataset[idx]
                face, wear = face.unsqueeze(0), wear.unsqueeze(0)
                pred, aux = model(face, wear, edge_index)
                all_preds.append(float(pred.item()))
                all_mins.append(idx)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"모델 예측 실패: {e}")

    if not all_preds:
        raise HTTPException(status_code=400, detail="분석 결과가 없습니다.")

    prediction = DrowsinessPrediction(
        session_id=session_id,
        drowsiness_level=all_preds[-1],
        confidence=1.0,
        details={"minute": all_mins[-1], "all_preds": all_preds}
    )
    return DrowsinessFinishResponse(
        session_id=session_id,
        prediction=prediction,
        message="졸음 예측이 완료되었습니다."
    )


# =========================
# 테스트용 API (신규 추가)
# =========================

@router.post("/drowsiness/testFinish", summary="[테스트용] Firebase PPG 데이터 로컬 저장")
def test_finish_drowsiness_detection(
        req: DrowsinessFinishRequest,
):
    """
    [테스트 전용] Session ID를 받아 Firebase에서 PPG 데이터만 가져와
    서버 로컬 경로(drowsiness_data/{session_id}/ppg_data.csv)에 저장합니다.
    인증, 세션 종료, ML 분석 등의 과정은 생략됩니다.
    """
    session_id = req.session_id

    try:
        from firebase_admin import db
        session_ref = db.reference(f"{session_id}")

        # 데이터가 존재하는지 간단히 확인
        if not session_ref.get():
            raise HTTPException(status_code=404, detail=f"세션 ID '{session_id}'를 찾을 수 없습니다.")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Firebase 세션 조회 중 오류 발생: {e}")

    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../drowsiness_data'))
    session_dir = os.path.join(base_dir, session_id)

    try:
        ppg_data_ref = session_ref.child("PPG_Data")
        ppg_data = ppg_data_ref.get()

        if ppg_data:
            ppg_list = [v for k, v in ppg_data.items()]
            df = pd.DataFrame(ppg_list)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values(by='timestamp').reset_index(drop=True)
            os.makedirs(session_dir, exist_ok=True)
            ppg_csv_path = os.path.join(session_dir, 'ppg_data.csv')
            df.to_csv(ppg_csv_path, index=False)
            message = f"PPG 데이터가 성공적으로 '{ppg_csv_path}' 경로에 저장되었습니다."
        else:
            message = f"세션 {session_id}에 대한 PPG 데이터가 없습니다. 폴더만 생성되었습니다."
            os.makedirs(session_dir, exist_ok=True)  # 데이터가 없어도 폴더는 생성

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Firebase PPG 데이터 처리 및 저장 실패: {e}")

    return {"message": message, "session_id": session_id}


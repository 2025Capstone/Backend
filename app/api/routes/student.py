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
from app.models.drowsiness_level import DrowsinessLevel
from app.services.hrv_analyzer import compute_hrv_and_features_from_firebase

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
        student_uid: str = Depends(get_current_student_uid),
        db_session: Session = Depends(get_db)
):
    session_id = req.session_id
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../drowsiness_data'))
    session_dir = os.path.join(base_dir, session_id)

    from firebase_admin import db as firebase_db

    try:
        session_ref = firebase_db.reference(f"{session_id}")
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
    
    # --- 1.5. 중복 분석 방지: 이미 분석된 데이터가 있는지 확인 ---
    print(f"[{session_id}] 🔍 중복 분석 확인 중...")
    existing_analysis = db_session.query(DrowsinessLevel).filter(
        DrowsinessLevel.video_id == video_id,
        DrowsinessLevel.student_uid == student_uid
    ).first()
    
    if existing_analysis:
        print(f"[{session_id}] ⚠️ 이미 분석 완료된 데이터 발견")
        raise HTTPException(
            status_code=409,  # 409 Conflict
            detail=f"해당 영상(video_id={video_id})에 대한 졸음 분석이 이미 완료되었습니다. 중복 분석을 방지하기 위해 요청이 거부되었습니다."
        )
    print(f"[{session_id}] ✅ 중복 분석 확인 완료 (분석 이력 없음)")

    # --- 2. PPG 데이터 수신 완료 대기 (Polling) ---
    try:
        polling_timeout = 180  # 최대 3분 대기
        polling_interval = 5   # 5초 간격으로 확인
        stability_threshold = 10 # 10초 동안 데이터 개수 변화 없으면 완료로 간주

        last_data_count = -1
        stable_time = 0
        waited_time = 0

        while waited_time < polling_timeout:
            ppg_node = session_ref.child("PPG_Data").get() or {}
            current_data_count = len(ppg_node)

            if current_data_count > last_data_count:
                # 데이터가 여전히 수신 중
                last_data_count = current_data_count
                stable_time = 0
            elif last_data_count > 0:
                # 데이터 개수 변화 없음
                stable_time += polling_interval

            if stable_time >= stability_threshold:
                # 업로드가 안정화되었으므로 완료로 판단
                print(f"✅ PPG 데이터 수신 완료. (총 {current_data_count}개)")
                break

            time.sleep(polling_interval)
            waited_time += polling_interval
        else:
            # 타임아웃 발생
            raise HTTPException(status_code=504, detail="PPG 데이터 수신 대기 시간을 초과했습니다.")

    except HTTPException as e:
        raise e # 타임아웃 예외는 그대로 전달
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PPG 데이터 수신 확인 중 오류 발생: {e}")


    # --- 3. 웨어러블 특징(HRV) 데이터 생성 ---
    try:
        df_wearable = compute_hrv_and_features_from_firebase(session_id)
        # 분석 결과를 디버깅용으로 저장 (선택 사항)
        os.makedirs(session_dir, exist_ok=True)
        wearable_csv_path = os.path.join(session_dir, 'wearable_features.csv')
        df_wearable.to_csv(wearable_csv_path, index=False)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"HRV 분석 실패: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"HRV 분석 중 서버 오류 발생: {e}")

    # --- 4. 랜드마크 데이터 로드 (파일 쓰기 완료 대기 포함) ---
    print(f"[{session_id}] 📂 Step 4: 랜드마크 데이터 로드 시작")
    if not os.path.isdir(session_dir):
        raise HTTPException(status_code=404, detail="Landmark 데이터 디렉토리가 존재하지 않습니다.")

    # WebSocket을 통한 파일 쓰기가 완료될 때까지 대기 (최대 2분)
    print(f"[{session_id}] ⏳ 랜드마크 파일 쓰기 완료 대기 중...")
    timeout, interval, waited = 120, 1, 0
    while waited < timeout:
        landmark_files = glob.glob(os.path.join(session_dir, 'landmarks_*.csv'))
        if not landmark_files:  # 파일이 아직 생성되지 않았으면 대기
            if waited % 10 == 0:  # 10초마다 로그 출력
                print(f"[{session_id}] ⏳ 랜드마크 파일 대기 중... ({waited}초 경과)")
            time.sleep(interval)
            waited += interval
            continue

        last_modified = max(os.path.getmtime(f) for f in landmark_files)
        # 마지막 파일 수정 후 2초 이상 지났으면 쓰기가 완료된 것으로 간주
        if time.time() - last_modified >= 2:
            print(f"[{session_id}] ✅ 랜드마크 파일 쓰기 완료 확인 (총 {len(landmark_files)}개 파일)")
            break
        time.sleep(interval)
        waited += interval
    else:
        raise HTTPException(status_code=500, detail="Landmark 데이터 저장 대기 시간을 초과했습니다.")

    # 랜드마크 파일 개수 확인 (병합은 PT 파일 생성 시 자동으로 수행됨)
    print(f"[{session_id}] ✅ 랜드마크 데이터 확인 완료 (총 {len(landmark_files)}개 파일)")
    
    # --- 5. 데이터 검증 ---
    print(f"[{session_id}] ✅ Step 5: 데이터 검증 완료")
    print(f"[{session_id}] 📊 HRV 세그먼트: {len(df_wearable)}개 (2분 단위)")
    print(f"[{session_id}] 📊 랜드마크 파일: {len(landmark_files)}개")
    
    # HRV 특징 차원 확인
    num_hrv_features = len([col for col in df_wearable.columns if col != 'timestamp'])
    print(f"[{session_id}] 📊 HRV 특징 차원: {num_hrv_features}개")
    if num_hrv_features != 39:
        raise HTTPException(
            status_code=500, 
            detail=f"HRV 특징 차원 불일치: {num_hrv_features}개 (기대값: 39개)"
        )

    # --- 6. AI 모델 예측 수행 및 DB 저장 (1분 단위) ---
    print(f"[{session_id}] 🤖 Step 6: AI 모델 예측 수행 시작 (1분 단위)")
    try:
        print(f"[{session_id}] 📦 PT 파일 생성 중...")
        pt_path = make_shard_and_pt(session_id, base_dir=base_dir, shard_size=150)
        if not (pt_path and os.path.exists(pt_path)):
            raise FileNotFoundError("PT 파일이 생성되지 않았습니다.")
        print(f"[{session_id}] ✅ PT 파일 생성 완료: {os.path.basename(pt_path)}")
        
        # 모델 로드
        print(f"[{session_id}] 🧠 AI 모델 로드 중...")
        edge_index_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../ml/edge_index_core.pt'))
        edge_index = torch.load(edge_index_path, map_location='cpu')
        model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../ml/best_model.pt'))
        model = MultimodalFatigueModel(num_classes=5)
        checkpoint = torch.load(model_path, map_location='cpu')
        model.load_state_dict(checkpoint.get('model', checkpoint))
        model.eval()
        print(f"[{session_id}] ✅ AI 모델 로드 완료")
        
        # 2분 단위로 예측 수행 (HRV 데이터와 동기화)
        # SEQ_LEN=12 shards × 150 frames/shard × (1/30) sec/frame = 60초 = 1분
        # 2분 = 24 shards
        SEQ_LEN = 24  # 2분에 해당하는 윈도우 개수
        STRIDE = 24   # 2분씩 이동 (2분 = 24 shards)
        
        print(f"[{session_id}] 📊 데이터셋 생성 중 (SEQ_LEN={SEQ_LEN}, STRIDE={STRIDE})...")
        dataset = SessionSequenceDataset(session_dir, seq_len=SEQ_LEN, stride=STRIDE)
        if len(dataset) == 0:
            raise ValueError("2분 이상 시청하지 않아 분석이 불가능합니다.")
        print(f"[{session_id}] ✅ 데이터셋 생성 완료 (총 {len(dataset)}개 시퀀스)")
        
        # HRV 데이터 개수 확인 (2분마다 1개)
        num_hrv_segments = len(df_wearable)
        
        # 랜드마크 데이터로 만들 수 있는 2분 단위 예측 개수
        num_landmark_2min_segments = len(dataset)
        
        # 실제 예측 가능한 개수는 랜드마크 데이터와 HRV 데이터 중 작은 값
        num_predictions = min(num_landmark_2min_segments, num_hrv_segments)
        
        print(f"[{session_id}] 📈 예측 정보: HRV 세그먼트={num_hrv_segments}, 랜드마크 세그먼트={num_landmark_2min_segments} (모두 2분 단위)")
        print(f"[{session_id}] 🎯 총 {num_predictions}개의 2분 단위 세그먼트 예측 시작")
        
        if num_predictions == 0:
            raise ValueError("예측 가능한 2분 단위 세그먼트가 없습니다.")
        
        all_preds = []
        with torch.no_grad():
            for idx in range(num_predictions):
                print(f"[{session_id}] 🔮 예측 중... [{idx+1}/{num_predictions}] (시간: {idx*2}~{(idx+1)*2}분)")
                
                # 랜드마크 데이터 (2분 단위)
                face, _, _ = dataset[idx]
                face = face.unsqueeze(0)  # [1, 24, 150, 478, 3]
                
                # HRV 데이터 (2분 단위, 1:1 매칭)
                hrv_row = df_wearable.iloc[idx]
                
                # HRV 특징 벡터 생성 (timestamp 제외한 39개 특징)
                feature_cols = [col for col in df_wearable.columns if col != 'timestamp']
                hrv_vector = hrv_row[feature_cols].values.astype(float).tolist()
                
                # 차원 검증
                if len(hrv_vector) != 39:
                    raise ValueError(f"HRV 특징 차원 오류: {len(hrv_vector)}개 (기대값: 39개)")
                
                wear = torch.tensor(hrv_vector, dtype=torch.float32).unsqueeze(0).unsqueeze(0)  # [1, 1, 39]
                # 24개 윈도우에 동일한 HRV 데이터 복제
                wear = wear.repeat(1, 24, 1)  # [1, 24, 39]
                
                pred, aux = model(face, wear, edge_index)
                drowsiness_score = float(pred.item())
                all_preds.append(drowsiness_score)
                print(f"[{session_id}] 📊 예측 결과: 졸음 점수 = {drowsiness_score:.4f}")
                
                # DB에 저장 (timestamp는 0부터 시작, 2분 단위)
                drowsiness_record = DrowsinessLevel(
                    video_id=video_id,
                    student_uid=student_uid,
                    timestamp=idx * 2,  # 0 = 0~2분, 2 = 2~4분, 4 = 4~6분, ...
                    drowsiness_score=drowsiness_score
                )
                db_session.add(drowsiness_record)
        
        print(f"[{session_id}] 💾 DB에 예측 결과 저장 중...")
        db_session.commit()
        print(f"[{session_id}] ✅ DB 저장 완료 (총 {len(all_preds)}개 레코드)")
        
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"모델 예측 실패: {e}")

    if not all_preds:
        raise HTTPException(status_code=400, detail="분석 결과가 없습니다.")

    print(f"[{session_id}] 🎉 졸음 탐지 분석 완료!")
    print(f"[{session_id}] 📊 최종 결과: 총 {len(all_preds)}개 세그먼트 (2분 단위), 마지막 졸음 점수 = {all_preds[-1]:.4f}")
    
    prediction = DrowsinessPrediction(
        session_id=session_id,
        drowsiness_level=all_preds[-1],
        confidence=1.0,
        details={"total_segments": len(all_preds), "all_preds": all_preds}
    )
    return DrowsinessFinishResponse(
        session_id=session_id,
        prediction=prediction,
        message=f"졸음 예측이 완료되었습니다. 총 {len(all_preds)}개의 2분 단위 세그먼트가 분석되었습니다."
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


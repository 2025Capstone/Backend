# /app/api/routes/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

# schemas 폴더의 관련 스키마 import (경로 확인)
from app.schemas.student import StudentAuthResponse, StudentCreate

# services 폴더의 관련 서비스 함수 import (경로 확인)
from app.services.student_service import (
    get_student_by_uid,
    create_student,
    get_student_by_email
)

# dependencies 폴더의 의존성 함수 import (경로 확인)
from app.dependencies.firebase_deps import get_verified_firebase_user # Firebase 토큰 검증
from app.dependencies.db import get_db # DB 세션 제공

# APIRouter 인스턴스 생성 (video.py와 동일한 방식)
router = APIRouter()

@router.post(
    "/verify-token",             # 이 라우터 파일 내에서의 경로
    response_model=StudentAuthResponse, # API 응답 형식 정의
    summary="Verify Firebase Token and Handle Student",
    description="""
    Firebase ID 토큰을 검증하고 해당 정보를 바탕으로 로컬 데이터베이스에서
    학생(student) 사용자를 조회하거나 새로 생성합니다.
    - 요청 헤더에 'Authorization: Bearer <FIREBASE_ID_TOKEN>' 포함 필요.
    - 성공 시 DB의 사용자 정보와 메시지 반환.
    - 신규 사용자 생성 시 이메일 중복 체크 수행.
    """
)
async def verify_token_and_handle_student(
    db: Session = Depends(get_db),              # DB 세션 의존성 주입
    decoded_token: dict = Depends(get_verified_firebase_user) # Firebase 토큰 검증 의존성 주입
):
    """
    Firebase 토큰을 검증하고 반환된 사용자 정보(decoded_token)를 사용하여
    데이터베이스에서 학생 사용자를 처리합니다.
    """
    try:
        # 1. Firebase 토큰에서 사용자 정보 추출
        uid = decoded_token['uid']
        email = decoded_token.get('email')
        name = decoded_token.get('name') # 이름은 선택 사항

        # 2. Email 필수 검사 (DB 스키마에서 nullable=False 이므로)
        if not email:
            # Firebase 계정에 이메일이 없는 경우에 대한 처리
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is required for registration but not found in your Firebase account."
            )

        # 3. DB에서 UID로 기존 사용자 조회 (서비스 함수 사용)
        db_student = get_student_by_uid(db=db, student_uid=uid)
        message = ""

        if db_student:
            # 4a. 기존 사용자가 있는 경우
            print(f"Existing student found (UID: {uid})")
            message = "Successfully logged in."
            # (선택 사항) 이름 등 Firebase 정보 기준으로 DB 업데이트 로직
            # 예: 이름이 DB와 다를 경우 업데이트
            # if name is not None and name != db_student.name:
            #     from app.schemas.student import StudentUpdate
            #     from app.services.student_service import update_student # update 함수 필요
            #     update_data = StudentUpdate(name=name)
            #     update_student(db=db, db_obj=db_student, obj_in=update_data)
            #     print(f"Student name updated for UID: {uid}")

        else:
            # 4b. 신규 사용자인 경우
            print(f"New student detected (UID: {uid})")

            # (중요) 다른 계정으로 동일 이메일이 이미 있는지 확인 (서비스 함수 사용)
            existing_student_by_email = get_student_by_email(db=db, email=email)
            if existing_student_by_email:
                # 이메일 중복 시 에러 처리 (정책에 따라 다름)
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"This email ({email}) is already registered with another account."
                )

            # 신규 사용자 DB에 생성 (서비스 함수 사용)
            student_in_data = StudentCreate(uid=uid, email=email, name=name)
            db_student = create_student(db=db, student_in=student_in_data)
            message = "New account created and logged in."

        # 5. 성공 응답 반환 (스키마에 맞춰서)
        return StudentAuthResponse(
            uid=db_student.uid,
            email=db_student.email,
            name=db_student.name,
            message=message
        )

    except HTTPException as http_exc:
        # HTTP 관련 예외는 그대로 전달 (DB 롤백은 필요시 추가)
        # db.rollback() # 필요하다면 추가
        raise http_exc
    except Exception as e:
        # 기타 예상치 못한 오류 발생 시 (DB 오류 포함 가능성)
        db.rollback() # DB 작업 중 오류 시 롤백
        print(f"An unexpected error occurred during token verification/student handling: {e}")
        # 상세 오류를 클라이언트에 노출하지 않는 것이 좋음
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred."
        )
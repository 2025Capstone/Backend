from app.schemas.admin import AdminAuthResponse, UserRoleResponse, UserRoleRequest, AdminLoginRequest
from app.schemas.student import StudentAuthResponse
from app.dependencies.firebase_deps import get_verified_firebase_user
from app.services.auth_service import handle_student_authentication, validate_admin_hash, create_student, StudentCreate
from fastapi import APIRouter, Depends, Body, HTTPException, status
from sqlalchemy.orm import Session
from app.dependencies.db import get_db
from app.schemas.token import TokenResponse
from app.services.token_service import rotate_refresh_token, create_access_token, create_refresh_token_with_rotation
from passlib.hash import bcrypt
import os
import logging
from app.core.config import settings
from pydantic import BaseModel
from app.models.admin_refresh_token import AdminRefreshToken
from datetime import datetime, timedelta
import jwt
from app.models.student import Student
from app.models.instructor import Instructor
import firebase_admin
from firebase_admin import auth as firebase_auth

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/verify-token",
    response_model=StudentAuthResponse,
    summary="학생 token 검증을 통한 로그인",
    description= """token을 검증하고, 학생 인증을 처리합니다."""
)
async def verify_token_and_handle_student(
        db: Session = Depends(get_db),
        decoded_token: dict = Depends(get_verified_firebase_user)
):
    return handle_student_authentication(db, decoded_token)




@router.post("/refresh", response_model=TokenResponse,
             summary="학생 리프레시 토큰 갱신",
             description="만료된 Access Token을 갱신합니다."
             )
def refresh_token(
        refresh_token: str = Body(..., embed=True),
        db: Session = Depends(get_db)
):
    access_token, new_refresh_token = rotate_refresh_token(db, refresh_token)
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token
    )


def create_admin_refresh_token(db: Session) -> str:
    from app.core.config import settings
    import jwt
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {"sub": "admin", "exp": expire}
    refresh_token = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    db_token = AdminRefreshToken(
        token=refresh_token,
        expired_at=expire,
        created_at=datetime.utcnow()
    )
    db.add(db_token)
    db.commit()
    db.refresh(db_token)
    return refresh_token

@router.post(
    "/admin-login",
    response_model=AdminAuthResponse,
    summary="관리자 로그인 (토큰 발급)",
    description=".env에 저장된 관리자 계정으로 로그인. 비밀번호는 bcrypt 해시로 검증."
)
async def admin_login(
    login_req: AdminLoginRequest = Body(...),
    db: Session = Depends(get_db)
):
    admin_id = os.getenv("ADMIN_ID")
    admin_pw_hash = os.getenv("ADMIN_PASSWORD_HASH")
    
    if not admin_id or not admin_pw_hash:
        logger.error("관리자 계정 정보가 서버에 설정되어 있지 않습니다.")
        raise HTTPException(status_code=500, detail="관리자 계정 정보가 서버에 설정되어 있지 않습니다.")
        
    if login_req.username != admin_id or not validate_admin_hash(login_req.password, admin_pw_hash):
        logger.info(f"관리자 로그인 실패 - 사용자명: {login_req.username}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="잘못된 관리자 계정 정보입니다.")
        
    logger.info(f"관리자 로그인 성공 - 사용자명: {login_req.username}")
    payload = {"sub": "admin"}
    access_token = create_access_token(payload)
    refresh_token = create_admin_refresh_token(db)
    return AdminAuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        message="관리자 로그인 성공"
    )

@router.post(
    "/admin-refresh",
    response_model=TokenResponse,
    summary="관리자 리프레시 토큰으로 액세스 토큰 재발급",
    description="관리자 리프레시 토큰을 검증하고, 새로운 access/refresh token을 발급합니다."
)
def admin_refresh_token(
    refresh_token: str = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    # 1. DB에서 토큰 존재 및 만료 여부 확인
    db_token = db.query(AdminRefreshToken).filter_by(token=refresh_token, is_revoked=False).first()
    if not db_token:
        raise HTTPException(status_code=401, detail="유효하지 않은 리프레시 토큰입니다.")
    if db_token.expired_at and db_token.expired_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="만료된 리프레시 토큰입니다.")
    # 2. JWT 디코드 검증
    try:
        payload = jwt.decode(refresh_token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("sub") != "admin":
            raise HTTPException(status_code=401, detail="잘못된 토큰 소유자입니다.")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="만료된 리프레시 토큰입니다.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="유효하지 않은 리프레시 토큰입니다.")
    # 3. 새 토큰 발급 및 기존 토큰 폐기(옵션)
    db_token.is_revoked = True
    db.commit()
    access_token = create_access_token({"sub": "admin"})
    new_refresh_token = create_admin_refresh_token(db)
    return TokenResponse(access_token=access_token, refresh_token=new_refresh_token)

@router.post(
    "/user-role",
    response_model=UserRoleResponse,
    summary="이메일로 유저 역할 반환",
    description="이메일(아이디)로 학생/강의자/관리자/없음 중 어떤 역할인지 반환합니다."
)
def get_user_role(
    req: UserRoleRequest = Body(...),
    db: Session = Depends(get_db)
):
    admin_id = os.getenv("ADMIN_ID")
    if req.email == admin_id:
        return UserRoleResponse(role="admin")
    # 1. 강의자 확인
    instructor = db.query(Instructor).filter_by(email=req.email).first()
    if instructor:
        return UserRoleResponse(role="instructor")
    # 2. 학생 확인 (DB)
    student = db.query(Student).filter_by(email=req.email).first()
    if student:
        return UserRoleResponse(role="student")
    # 3. 학생 확인 (파이어베이스)
    try:
        firebase_user = firebase_auth.get_user_by_email(req.email)
        if firebase_user:
            # DB에 저장
            student_in_data = StudentCreate(
                uid=firebase_user.uid,
                email=firebase_user.email,
                name=firebase_user.display_name or ""
            )
            create_student(db=db, student_in=student_in_data)
            return UserRoleResponse(role="student")
    except firebase_auth.UserNotFoundError:
        pass
    except Exception as e:
        # firebase 연결 문제 등 기타 에러는 none 반환
        pass
    # 4. 해당 없음
    return UserRoleResponse(role="none")
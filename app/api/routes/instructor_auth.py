from fastapi import APIRouter, Depends, Body, HTTPException
from sqlalchemy.orm import Session
from app.dependencies.db import get_db
from app.schemas.instructor_auth import (
    InstructorLoginRequest, InstructorAuthResponse,
    InstructorCreate, InstructorCreateResponse,
    InstructorTokenRefreshRequest, InstructorTokenResponse
)
from app.services.instructor_auth_service import authenticate_instructor
from app.services.instructor_service import create_instructor
from app.services.instructor_token_service import rotate_instructor_refresh_token

router = APIRouter()

@router.post("/register", response_model=InstructorCreateResponse, summary="강의자 회원가입")
def instructor_register(
    instructor_in: InstructorCreate = Body(...),
    db: Session = Depends(get_db)
):
    """
    강의자 회원가입 (비밀번호는 bcrypt 해시로 저장)
    """
    return create_instructor(db, instructor_in)

@router.post("/login", response_model=InstructorAuthResponse, summary="강의자 로그인")
def instructor_login(
    login_req: InstructorLoginRequest = Body(...),
    db: Session = Depends(get_db)
):
    """
    강의자 로그인
    - 이메일과 비밀번호를 받아 인증
    - 성공 시 access/refresh token 반환
    """
    return authenticate_instructor(db, login_req.email, login_req.password)

@router.post("/refresh", response_model=InstructorTokenResponse, summary="강의자 토큰 재발급")
def instructor_refresh_token(
    req: InstructorTokenRefreshRequest = Body(...),
    db: Session = Depends(get_db)
):
    """
    강의자 전용 refresh token으로 access/refresh 토큰 재발급
    """
    access_token, refresh_token = rotate_instructor_refresh_token(db, req.refresh_token)
    return InstructorTokenResponse(access_token=access_token, refresh_token=refresh_token)
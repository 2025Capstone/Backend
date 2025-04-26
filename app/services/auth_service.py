from app.services.token_service import create_access_token, create_refresh_token_with_rotation

from app.schemas.student import StudentAuthResponse, StudentCreate
from app.services.student_service import (
    create_student,
    get_student_by_email
)
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

from sqlalchemy.orm import Session
from app.dependencies.db import get_db
from app.services.student_service import get_student_by_uid
from app.core.config import settings


def handle_student_authentication(
        db: Session,
        decoded_token: dict
) -> StudentAuthResponse:
    """
    Firebase 토큰을 검증하고 반환된 사용자 정보(decoded_token)를 사용하여
    데이터베이스에서 학생 사용자를 처리하고 응답 객체 반환
    """
    uid = decoded_token['uid']
    email = decoded_token.get('email')
    name = decoded_token.get('name')

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is required for registration but not found in your Firebase account."
        )

    db_student = get_student_by_uid(db=db, student_uid=uid)
    message = ""

    if db_student:
        message = "Successfully logged in."
    else:
        existing_student_by_email = get_student_by_email(db=db, email=email)
        if existing_student_by_email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"This email ({email}) is already registered with another account."
            )

        student_in_data = StudentCreate(uid=uid, email=email, name=name)
        db_student = create_student(db=db, student_in=student_in_data)
        message = "New account created and logged in."

    # 토큰 생성
    payload = {"sub": db_student.uid}
    access_token = create_access_token(payload)
    refresh_token = create_refresh_token_with_rotation(db, db_student.uid)

    return StudentAuthResponse(
        uid=db_student.uid,
        email=db_student.email,
        name=db_student.name,
        message=message,
        access_token=access_token,
        refresh_token=refresh_token
    )




bearer_scheme = HTTPBearer()

# 토큰 검증 실패용 공통 예외
credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)

async def get_current_student(
        credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
        db: Session = Depends(get_db),
):
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        uid: str = payload.get("sub")
        if uid is None:
            # 여기서 바로 정의해 둔 예외를 던집니다
            raise credentials_exception
    except JWTError:
        # 토큰 자체가 잘못됐거나 만료된 경우
        raise credentials_exception

    student = get_student_by_uid(db=db, student_uid=uid)
    if not student:
        # 토큰은 유효하지만, 해당 uid의 학생이 DB에 없을 때
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return student
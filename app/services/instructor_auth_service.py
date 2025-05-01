from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.instructor import Instructor
from app.schemas.instructor_auth import InstructorAuthResponse
from app.services.instructor_token_service import create_instructor_access_token, create_instructor_refresh_token_with_rotation
from app.core.config import settings
from passlib.hash import bcrypt


def authenticate_instructor(db: Session, email: str, password: str) -> InstructorAuthResponse:
    instructor = db.query(Instructor).filter(Instructor.email == email).first()
    if not instructor or not bcrypt.verify(password, instructor.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")
    if instructor.is_approved != 1:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="관리자 승인 대기 중입니다.")

    payload = {"sub": str(instructor.id)}
    access_token = create_instructor_access_token(payload)
    refresh_token = create_instructor_refresh_token_with_rotation(db, instructor.id)

    return InstructorAuthResponse(
        id=instructor.id,
        name=instructor.name,
        email=instructor.email,
        access_token=access_token,
        refresh_token=refresh_token,
        message="Successfully logged in."
    )

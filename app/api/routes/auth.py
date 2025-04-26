from app.schemas.student import StudentAuthResponse
from app.dependencies.firebase_deps import get_verified_firebase_user
from app.services.auth_service import handle_student_authentication
from fastapi import APIRouter, Depends, Body
from sqlalchemy.orm import Session
from app.dependencies.db import get_db
from app.schemas.token import TokenResponse
from app.services.token_service import rotate_refresh_token


router = APIRouter()

@router.post(
    "/verify-token",
    response_model=StudentAuthResponse,
    summary="Verify Firebase Token and Handle Student",
    description= """token을 검증하고, 학생 인증을 처리합니다."""
)
async def verify_token_and_handle_student(
        db: Session = Depends(get_db),
        decoded_token: dict = Depends(get_verified_firebase_user)
):
    return handle_student_authentication(db, decoded_token)




@router.post("/refresh", response_model=TokenResponse,
             summary="Refresh Access Token",
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
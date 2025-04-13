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
    description="""
    Firebase ID 토큰을 검증하고 해당 정보를 바탕으로 로컬 데이터베이스에서
    학생(student) 사용자를 조회하거나 새로 생성합니다.
    - 요청 헤더에 'Authorization: Bearer <FIREBASE_ID_TOKEN>' 포함 필요.
    """
)
async def verify_token_and_handle_student(
        db: Session = Depends(get_db),
        decoded_token: dict = Depends(get_verified_firebase_user)
):
    return handle_student_authentication(db, decoded_token)




@router.post("/refresh", response_model=TokenResponse, summary="Refresh Access Token")
def refresh_token(
        refresh_token: str = Body(..., embed=True),
        db: Session = Depends(get_db)
):
    access_token, new_refresh_token = rotate_refresh_token(db, refresh_token)
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token
    )
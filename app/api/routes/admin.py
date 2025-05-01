from fastapi import APIRouter, Depends, HTTPException, Body, status
from sqlalchemy.orm import Session
from app.dependencies.db import get_db
from app.models.instructor import Instructor
from app.schemas.instructor_auth import InstructorAuthResponse, InstructorCreateResponse
from app.services.admin_auth_service import authenticate_admin
from app.services.instructor_service import approve_instructor_by_id
from app.schemas.admin import AdminLoginRequest, AdminLoginResponse
from app.dependencies.admin_auth import get_current_admin, get_current_admin_token

router = APIRouter(
    dependencies=[Depends(get_current_admin_token)]
)


@router.post("/approve-instructor/{instructor_id}", summary="교수자 승인", response_model=InstructorCreateResponse)
def approve_instructor(
    instructor_id: int,
    db: Session = Depends(get_db)
):
    """
    교수자 승인 (관리자 권한 필요)
    """
    result = approve_instructor_by_id(db, instructor_id)
    return InstructorCreateResponse(
        id=result["id"],
        name=result["name"],
        email=result["email"],
        message=result["message"]
    )

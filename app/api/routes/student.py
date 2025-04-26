from fastapi import APIRouter, Depends
from app.services.auth_service import get_current_student

router = APIRouter(
    dependencies=[Depends(get_current_student)]
)

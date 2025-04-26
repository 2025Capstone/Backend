from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.schemas.student import StudentCreate
from app.services.student_service import create_student
from app.dependencies.db import get_db
from app.dependencies.firebase_deps import get_verified_firebase_user

router = APIRouter(
    dependencies=[Depends(get_verified_firebase_user)]
)

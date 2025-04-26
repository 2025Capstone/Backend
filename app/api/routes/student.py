from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.schemas.student import StudentCreate
from app.services.student_service import create_student
from app.dependencies.db import get_db

router = APIRouter()


# /app/schemas/student.py
from pydantic import BaseModel, EmailStr
from typing import Optional


class StudentAuthResponse(BaseModel):
    uid: str
    email: str
    name: Optional[str]
    access_token: str
    refresh_token: str

    class Config:
        orm_mode = True


class StudentCreate(BaseModel):
    uid: str
    email: str
    name: Optional[str]

    class Config:
        orm_mode = True

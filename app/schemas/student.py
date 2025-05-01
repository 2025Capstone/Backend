# /app/schemas/student.py
from pydantic import BaseModel, EmailStr
from typing import Optional, List


class StudentAuthResponse(BaseModel):
    uid: str
    email: str
    name: Optional[str]
    access_token: str
    refresh_token: str

    class Config:
        from_attributes = True


class StudentCreate(BaseModel):
    uid: str
    email: str
    name: Optional[str]

    class Config:
        from_attributes = True



class EnrollmentRequest(BaseModel):
    lecture_id: int

class EnrollmentCancelRequest(BaseModel):
    lecture_id: int

class EnrollmentResponse(BaseModel):
    message: str

class EnrollmentCancelResponse(BaseModel):
    message: str


class LectureVideoListRequest(BaseModel):
    lecture_id: int

class LectureVideoInfo(BaseModel):
    id: int
    index: int
    title: str
    duration: int
    upload_at: str
    watched_percent : int

class LectureVideoListResponse(BaseModel):
    videos: List[LectureVideoInfo]

class VideoLinkRequest(BaseModel):
    video_id: int

class VideoLinkResponse(BaseModel):
    s3_link: str
    watched_percent: int

class StudentProfileResponse(BaseModel):
    email: str
    name: str | None

class StudentNameUpdateRequest(BaseModel):
    name: str

class StudentNameUpdateResponse(BaseModel):
    message: str
    name: str | None

class VideoProgressUpdateRequest(BaseModel):
    video_id: int
    watched_percent: int  # 0~100

class VideoProgressUpdateResponse(BaseModel):
    message: str

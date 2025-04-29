from fastapi import Form
from pydantic import BaseModel
from typing import Optional

class VideoBase(BaseModel):
    lecture_id: int
    title: str

    @classmethod
    def as_form(cls, lecture_id: int = Form(...), title: str = Form(...)):
        return cls(lecture_id=lecture_id, title=title)

class VideoCreate(VideoBase):
    pass

class VideoResponse(VideoBase):
    id: int
    s3_link: str
    duration: int
    index: int
    upload_at: str
    is_public: int

    class Config:
        from_attributes = True

class VideoVisibilityUpdateRequest(BaseModel):
    video_id: int
    is_public: int  # 1=공개, 0=비공개

class VideoVisibilityUpdateResponse(BaseModel):
    id: int
    is_public: int
    message: str
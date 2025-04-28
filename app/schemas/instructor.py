from pydantic import BaseModel
from typing import Optional, List

class LectureCreate(BaseModel):
    name: str

class LectureCreateResponse(BaseModel):
    id: int
    name: str
    instructor_id: int
    message: Optional[str] = None

class MyLectureInfo(BaseModel):
    id: int
    name: str

class MyLectureListResponse(BaseModel):
    lectures: List[MyLectureInfo]
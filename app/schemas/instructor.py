from pydantic import BaseModel
from typing import Optional

class LectureCreate(BaseModel):
    name: str

class LectureCreateResponse(BaseModel):
    id: int
    name: str
    instructor_id: int
    message: Optional[str] = None
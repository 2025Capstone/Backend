from pydantic import BaseModel

class LectureBase(BaseModel):
    id: int
    name: str
    instructor_name: str
    schedule: str
    classroom: str

    class Config:
        from_attributes = True

class LectureListResponse(BaseModel):
    lectures: list[LectureBase]

class LectureVisibilityUpdateRequest(BaseModel):
    lecture_id: int
    is_public: bool

class LectureVisibilityUpdateResponse(BaseModel):
    id: int
    is_public: bool
    message: str

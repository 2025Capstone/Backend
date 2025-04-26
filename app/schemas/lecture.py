from pydantic import BaseModel

class LectureBase(BaseModel):
    id: int
    instructor_id: int
    name: str

    class Config:
        from_attributes = True

class LectureListResponse(BaseModel):
    lectures: list[LectureBase]

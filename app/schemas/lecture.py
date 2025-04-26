from pydantic import BaseModel

class LectureBase(BaseModel):
    id: int
    name: str
    instructor_name: str

    class Config:
        from_attributes = True

class LectureListResponse(BaseModel):
    lectures: list[LectureBase]

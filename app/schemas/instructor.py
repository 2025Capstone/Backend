from pydantic import BaseModel
from typing import Optional, List

class AdminLectureCreate(BaseModel):
    name: str
    instructor_id: int
    schedule: str | None = None
    classroom: str | None = None

class LectureCreate(BaseModel):
    name: str

class LectureCreateResponse(BaseModel):
    id: int
    name: str
    instructor_id: int
    schedule: str | None = None
    classroom: str | None = None
    message: Optional[str] = None

class MyLectureInfo(BaseModel):
    id: int
    name: str

class MyLectureListResponse(BaseModel):
    lectures: List[MyLectureInfo]

class LectureStudentListRequest(BaseModel):
    lecture_id: int

class LectureStudentInfo(BaseModel):
    uid: str
    email: str
    name: str | None

class LectureStudentListResponse(BaseModel):
    students: List[LectureStudentInfo]

class BulkEnrollRequest(BaseModel):
    lecture_id: int
    student_uid_list: list[str]

class BulkEnrollResponse(BaseModel):
    enrolled: list[str]
    already_enrolled: list[str]
    not_found: list[str]
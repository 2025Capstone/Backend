# /app/schemas/student.py
from pydantic import BaseModel, EmailStr
from typing import Optional

# --- Firebase 인증 기반 스키마 ---

class StudentBase(BaseModel):
    """ 학생 정보의 기본 필드 """
    email: EmailStr     # Firebase에서 가져오며, DB에서 필수
    name: Optional[str] = None # Firebase에서 선택 사항, DB에서도 nullable

class StudentCreate(StudentBase):
    """ DB에 학생 생성 시 필요한 정보 (Firebase에서 받아옴) """
    uid: str # Firebase UID 필수

class StudentUpdate(BaseModel):
    """ 학생 정보 업데이트 시 허용할 정보 (필요에 따라 정의) """
    name: Optional[str] = None
    # email 변경 로직은 신중하게 결정

class StudentInDBBase(StudentBase):
    """ DB에 저장된 학생 정보 기본 형태 """
    uid: str

    class Config:
        from_attributes = True # Pydantic v2+ (이전 버전은 orm_mode = True)

class Student(StudentInDBBase):
    """ API 등에서 사용할 학생 정보 모델 """
    pass

class StudentAuthResponse(Student): # 이름 변경 (기존 Student와 구분)
    """ 인증 API 엔드포인트의 응답 모델 """
    message: str

# --- 기존 스키마 (더 이상 사용되지 않을 수 있음) ---
# class StudentCreateOriginal(BaseModel): # 이름 변경 또는 삭제
#     name: str
#     email: EmailStr
#     # password 필드는 더 이상 사용 안함

# class StudentOriginal(StudentCreateOriginal): # 이름 변경 또는 삭제
#     id: int
#     class Config:
#         from_attributes = True
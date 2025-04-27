from pydantic import BaseModel, EmailStr

class InstructorLoginRequest(BaseModel):
    email: EmailStr
    password: str

class InstructorCreate(BaseModel):
    name: str
    email: EmailStr
    password: str

class InstructorCreateResponse(BaseModel):
    id: int
    name: str
    email: str
    message: str = None

class InstructorAuthResponse(BaseModel):
    id: int
    name: str
    email: str
    access_token: str
    refresh_token: str
    message: str = None

    class Config:
        from_attributes = True

class InstructorTokenRefreshRequest(BaseModel):
    refresh_token: str

class InstructorTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
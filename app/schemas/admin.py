from pydantic import BaseModel, EmailStr

class AdminLoginRequest(BaseModel):
    username: str
    password: str

class AdminAuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    message: str

class UserRoleRequest(BaseModel):
    email: str

class UserRoleResponse(BaseModel):
    role: str  # 'student', 'instructor', 'admin', 'none'

class AdminLoginResponse(BaseModel):
    id: int
    email: str
    access_token: str
    message: str = None

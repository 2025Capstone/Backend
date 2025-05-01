from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.admin import Admin
from app.schemas.admin import AdminLoginResponse
from passlib.hash import bcrypt
from app.services.admin_token_service import create_admin_access_token

def authenticate_admin(db: Session, email: str, password: str) -> AdminLoginResponse:
    admin = db.query(Admin).filter(Admin.email == email).first()
    if not admin or not bcrypt.verify(password, admin.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")

    payload = {"sub": str(admin.id)}
    access_token = create_admin_access_token(payload)

    return AdminLoginResponse(
        id=admin.id,
        email=admin.email,
        access_token=access_token,
        message="Successfully logged in."
    )

import jwt
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.instructor_refresh_token import InstructorRefreshToken
from app.core.config import settings

def create_instructor_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def create_instructor_refresh_token_with_rotation(db: Session, instructor_id: int) -> str:
    to_encode = {"sub": str(instructor_id)}
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    refresh_token = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    db_token = InstructorRefreshToken(
        token=refresh_token,
        instructor_id=instructor_id,
        expired_at=expire
    )
    db.add(db_token)
    db.commit()
    db.refresh(db_token)
    return refresh_token

def rotate_instructor_refresh_token(db: Session, refresh_token: str) -> tuple[str, str]:
    try:
        payload = jwt.decode(refresh_token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        instructor_id = payload.get("sub")
        if not instructor_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

        db_token = db.query(InstructorRefreshToken).filter_by(token=refresh_token).first()
        if not db_token or db_token.is_revoked:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token is invalid or already used")

        db_token.is_revoked = True
        db.commit()

        new_access_token = create_instructor_access_token({"sub": instructor_id})
        new_refresh_token = create_instructor_refresh_token_with_rotation(db, int(instructor_id))

        return new_access_token, new_refresh_token

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

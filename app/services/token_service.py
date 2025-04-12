import jwt
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.token import RefreshToken
from app.core.config import settings

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def create_refresh_token_with_rotation(db: Session, uid: str) -> str:
    to_encode = {"sub": uid}
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    refresh_token = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    db_token = RefreshToken(
        token=refresh_token,
        student_uid=uid,
        expired_at=expire
    )
    db.add(db_token)
    db.commit()
    db.refresh(db_token)

    return refresh_token

def rotate_refresh_token(db: Session, refresh_token: str) -> tuple[str, str]:
    try:
        payload = jwt.decode(refresh_token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        uid = payload.get("sub")
        if not uid:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

        db_token = db.query(RefreshToken).filter_by(token=refresh_token).first()
        if not db_token or db_token.is_revoked:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token is invalid or already used")

        db_token.is_revoked = True
        db.commit()

        new_access_token = create_access_token({"sub": uid})
        new_refresh_token = create_refresh_token_with_rotation(db, uid)

        return new_access_token, new_refresh_token

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

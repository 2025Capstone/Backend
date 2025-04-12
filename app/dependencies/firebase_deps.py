# /app/dependencies/firebase_deps.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from firebase_admin import auth

# Bearer 스키마 인스턴스 생성
bearer_scheme = HTTPBearer()

async def get_verified_firebase_user(
    token: HTTPAuthorizationCredentials = Depends(bearer_scheme)
) -> dict:
    """
    Request의 Authorization 헤더에서 Bearer 토큰을 추출하고,
    Firebase Admin SDK를 사용하여 토큰을 검증합니다.
    성공 시 디코딩된 토큰 정보를 반환하고, 실패 시 HTTPException을 발생시킵니다.
    """
    id_token = token.credentials # 실제 토큰 문자열 추출
    try:
        # Firebase ID 토큰 검증
        # check_revoked=True 옵션은 필요에 따라 추가 (세션 해지 확인 시)
        decoded_token = auth.verify_id_token(id_token)
        # 여기서 decoded_token 딕셔너리에는 uid, email, name 등 포함됨
        return decoded_token
    except auth.ExpiredIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Firebase ID token has expired.",
            headers={"WWW-Authenticate": "Bearer error=\"invalid_token\", error_description=\"The token has expired\""},
        )
    except auth.InvalidIdTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Firebase ID token: {e}",
            headers={"WWW-Authenticate": "Bearer error=\"invalid_token\", error_description=\"The token is invalid\""},
        )
    except Exception as e:
        # Firebase Admin SDK에서 발생할 수 있는 다른 예외 처리
        print(f"Unexpected error during Firebase token verification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal server error occurred during token verification.",
        )
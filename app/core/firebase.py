# /app/core/firebase.py
import os
import firebase_admin
from firebase_admin import credentials
from dotenv import load_dotenv

def initialize_firebase():
    """
    환경 변수에서 서비스 계정 키 경로를 로드하고
    Firebase Admin SDK를 초기화합니다.
    애플리케이션 시작 시 한 번 호출되어야 합니다.
    """
    load_dotenv() # .env 파일 로드

    key_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY_PATH")
    if not key_path:
        raise ValueError("FIREBASE_SERVICE_ACCOUNT_KEY_PATH 환경 변수가 설정되지 않았습니다.")
    if not os.path.exists(key_path):
        raise FileNotFoundError(f"Firebase 서비스 계정 키 파일을 찾을 수 없습니다: {key_path}")

    try:
        # 이미 초기화되었는지 확인 (선택적이지만 재초기화 방지)
        if not firebase_admin._apps:
            cred = credentials.Certificate(key_path)
            firebase_admin.initialize_app(cred)
            # print("Firebase Admin SDK가 성공적으로 초기화되었습니다.")
        else:
            print("Firebase Admin SDK가 이미 초기화되어 있습니다.")
    except Exception as e:
        print(f"Firebase Admin SDK 초기화 실패: {e}")
        # 실제 운영 환경에서는 초기화 실패 시 적절한 조치를 취해야 합니다.
        raise e
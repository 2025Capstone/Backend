import os
import firebase_admin
from firebase_admin import credentials
from dotenv import load_dotenv

def initialize_firebase():
    """
    환경 변수에서 서비스 계정 키 경로와 데이터베이스 URL을 로드하고
    Firebase Admin SDK를 초기화합니다.
    애플리케이션 시작 시 한 번 호출되어야 합니다.
    """
    load_dotenv() # .env 파일 로드

    key_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY_PATH")
    database_url = os.getenv("FIREBASE_DATABASE_URL")

    # --- 👇 [디버깅] 터미널에 환경 변수 값 출력 ---
    print("="*50)
    print(f"[DEBUG] Firebase Key Path: {key_path}")
    print(f"[DEBUG] Firebase Database URL: {database_url}")
    print("="*50)
    # --- 👆 [디버깅] 코드 끝 ---

    if not key_path:
        raise ValueError("FIREBASE_SERVICE_ACCOUNT_KEY_PATH 환경 변수가 설정되지 않았습니다.")
    if not database_url:
        raise ValueError("FIREBASE_DATABASE_URL 환경 변수가 설정되지 않았습니다.")
    if not os.path.exists(key_path):
        raise FileNotFoundError(f"Firebase 서비스 계정 키 파일을 찾을 수 없습니다: {key_path}")

    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate(key_path)
            firebase_admin.initialize_app(cred, {
                'databaseURL': database_url
            })
            print("Firebase Admin SDK가 성공적으로 초기화되었습니다.") # <-- 초기화 성공 메시지 추가
        else:
            print("Firebase Admin SDK가 이미 초기화되어 있습니다.")
    except Exception as e:
        print(f"Firebase Admin SDK 초기화 실패: {e}")
        raise e
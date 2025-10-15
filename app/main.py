# /app/main.py
import logging
from logging.handlers import RotatingFileHandler
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager


from fastapi import FastAPI
from contextlib import asynccontextmanager # Lifespan 사용 위해 import

# --- Core / Config ---
from app.core.firebase import initialize_firebase # Firebase 초기화 함수 import

# --- API Routers ---
from app.api.routes import auth as auth_router
from app.api.routes import websocket as websocket_router # websocket 라우터 import
from app.api.routes import instructor_auth as instructor_auth_router # instructor 라우터 import
from app.api.routes import instructor as instructor_router # instructor 라우터 import
from app.api.routes import student as student_router # student 라우터 import
from app.api.routes import admin as admin_router # admin 라우터 import


# --- 미들웨어 import ---
from fastapi.middleware.cors import CORSMiddleware




# --- 👇 1. 로깅 설정 추가 ---
# 로그 포맷터 생성 (시간 - 로거이름 - 로그레벨 - 메시지)
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# error.log 파일 핸들러 생성 (파일 크기가 5MB를 넘으면 새 파일로 교체)
log_handler = RotatingFileHandler('error.log', maxBytes=5*1024*1024, backupCount=3)
log_handler.setFormatter(log_formatter)

# 로거 객체 생성 후 핸들러 추가
logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)  # ERROR 레벨 이상의 로그만 파일에 기록
logger.addHandler(log_handler)
# ------------------------------------



# --- Lifespan (애플리케이션 시작/종료 이벤트) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 애플리케이션 시작 시 실행될 코드
    initialize_firebase() # <<<--- 여기에서 Firebase 초기화 함수를 호출합니다!
    # 다른 시작 시 필요한 작업들 (예: DB 커넥션 풀 생성 등)

    yield

# --- FastAPI App Instance ---
app = FastAPI(
    title="ZzzCoach API",
    lifespan=lifespan # <<<--- FastAPI 앱 생성 시 lifespan을 등록합니다!
)

# --- 👇 2. 전역 예외 처리 핸들러 추가 ---
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # [핵심] 예상치 못한 모든 오류를 error.log 파일에 기록합니다.
    # exc_info=True를 통해 전체 에러 추적 내용을 기록할 수 있습니다.
    logger.error(f"처리되지 않은 예외 발생: {exc}", exc_info=True)
    
    # 프론트엔드에는 간단하고 안전한 메시지를 반환합니다.
    return JSONResponse(
        status_code=500,
        content={"detail": "서버 내부에서 예상치 못한 오류가 발생했습니다."},
    )
# ---------------------------------------------


# --- CORS 미들웨어 설정 ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 라우트 등록 ---
app.include_router(
    auth_router.router,
    prefix="/api/v1/auth",
    tags=["Authentication"]
)





app.include_router(
    websocket_router.websocket_router, # websocket.py의 websocket_router 객체 사용
    prefix="",
    tags=["websocket"]
)

app.include_router(
    instructor_auth_router.router,
    prefix="/api/v1/instructors-auth",
    tags=["Authentication"]
)

app.include_router(
    admin_router.router,
    prefix="/api/v1/admin",
    tags=["admin"]
)

app.include_router(
    instructor_router.router,
    prefix="/api/v1/instructors",
    tags=["instructors"]
)

app.include_router(
    student_router.router,
    prefix="/api/v1/students",
    tags=["students"]
)
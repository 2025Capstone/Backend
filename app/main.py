# /app/main.py
import logging
import time
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



logging.basicConfig(
    level=logging.INFO, # INFO 레벨 이상의 로그를 모두 출력하도록 설정
    format="%(asctime)s - %(levelname)s - %(message)s", # 로그 형식 지정
    force=True # 다른 라이브러리에 의해 이미 설정되었더라도 강제로 재설정
)




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

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()

    # 다음 미들웨어나 실제 API 엔드포인트를 호출
    response = await call_next(request)

    process_time = time.time() - start_time

    # 응답 헤더에 처리 시간 추가
    response.headers["X-Process-Time"] = str(process_time)

    # 로그에 API 경로와 처리 시간 기록
    logging.info(
        f"Request processed: {request.method} {request.url.path} - Completed in {process_time:.4f} secs"
    )

    return response



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
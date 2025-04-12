# /app/main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager # Lifespan 사용 위해 import

# --- Core / Config ---
from app.core.firebase import initialize_firebase # Firebase 초기화 함수 import

# --- API Routers ---
from app.api.routes import auth as auth_router
from app.api.routes import video as video_router # video 라우터 이름 확인
from app.api.routes import websocket as websocket_router # websocket 라우터 이름 확인
# 기존 student 라우터는 주석 처리 또는 삭제
# from app.api.routes import student as student_router

# --- 미들웨어 import ---
from fastapi.middleware.cors import CORSMiddleware

# --- Lifespan (애플리케이션 시작/종료 이벤트) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 애플리케이션 시작 시 실행될 코드
    print("애플리케이션 시작...")
    initialize_firebase() # <<<--- 여기에서 Firebase 초기화 함수를 호출합니다!
    # 다른 시작 시 필요한 작업들 (예: DB 커넥션 풀 생성 등)
    yield
    # 애플리케이션 종료 시 실행될 코드
    print("애플리케이션 종료...")

# --- FastAPI App Instance ---
app = FastAPI(
    title="FastAPI Example",
    lifespan=lifespan # <<<--- FastAPI 앱 생성 시 lifespan을 등록합니다!
)

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
    video_router.router, # video.py의 router 객체 사용
    prefix="/api/v1/videos",
    tags=["videos"]
)
app.include_router(
    websocket_router.router, # websocket.py의 router 객체 사용
    prefix="/ws",
    tags=["websocket"]
)
# app.include_router(student.router, prefix="/students", tags=["students"]) # 주석 처리 또는 삭제

# --- 루트 경로 (선택 사항) ---
@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "API is running!"}
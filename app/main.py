from fastapi import FastAPI
from app.api.routes import student
from app.api.routes import video
from app.api.routes import websocket
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="FastAPI Example")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 또는 ["http://localhost:3000"] 처럼 특정 도메인 지정
    allow_credentials=True,
    allow_methods=["*"],  # OPTIONS 포함
    allow_headers=["*"],
)

# 라우트 등록
app.include_router(student.router, prefix="/students", tags=["students"])
app.include_router(video.router, prefix="/videos", tags=["videos"])

app.include_router(websocket.router, prefix="/ws", tags=["websocket"])
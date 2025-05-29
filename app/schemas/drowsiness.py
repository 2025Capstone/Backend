from pydantic import BaseModel, Field
from typing import Optional, List

class DrowsinessStartRequest(BaseModel):
    video_id: int = Field(..., description="분석할 영상 ID")

class DrowsinessStartResponse(BaseModel):
    session_id: str = Field(..., description="졸음 탐지 세션 ID")
    message: str = Field(..., description="세션 시작 안내/상태 메시지")

class DrowsinessVerifyRequest(BaseModel):
    session_id: str = Field(..., description="졸음 탐지 세션 ID")
    code: str = Field(..., description="웨어러블 인증 코드")

class DrowsinessVerifyResponse(BaseModel):
    session_id: str = Field(..., description="졸음 탐지 세션 ID")
    verified: bool = Field(..., description="웨어러블 연동 성공 여부")
    message: str = Field(..., description="상태 메시지")

class DrowsinessFinishRequest(BaseModel):
    session_id: str = Field(..., description="졸음 탐지 세션 ID")

class DrowsinessPrediction(BaseModel):
    drowsiness_level: float = Field(..., description="예측된 졸음 레벨 (1~5)")
    confidence: float = Field(..., description="신뢰도")
    details: Optional[dict] = Field(None, description="추가 예측 정보")

class DrowsinessFinishResponse(BaseModel):
    session_id: str = Field(..., description="졸음 탐지 세션 ID")
    prediction: DrowsinessPrediction
    message: str = Field(..., description="상태 메시지")

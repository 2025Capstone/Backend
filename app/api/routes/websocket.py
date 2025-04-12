from fastapi import APIRouter, WebSocket
import json
from app.ml.predictor import predict_drowsiness

router = APIRouter()

@router.websocket("/landmarks")
async def websocket_landmarks(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            landmarks = json.loads(data)
            # print(f"Received landmarks count: {len(landmarks)}")
            # print(f"First landmark coordinates: {landmarks[:3]}")

            result = predict_drowsiness(landmarks)
            print("Prediction result:", result)

    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        print("WebSocket connection closed")
        await websocket.close()
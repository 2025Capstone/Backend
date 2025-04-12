import os
import torch
import torch.nn as nn
import numpy as np

from app.ml.model import FaceLandmarksModelAttention, DrowsinessModel

# 현재 파일 위치를 기준으로 절대 경로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # predictor.py의 경로
MODEL_PATH_1 = os.path.join(BASE_DIR, "model1.pt")
MODEL_PATH_2 = os.path.join(BASE_DIR, "model2.pt")

# 모델 로드
model1 = FaceLandmarksModelAttention()
model1.load_state_dict(torch.load(MODEL_PATH_1, map_location=torch.device("cpu")))
model1.eval()

model2 = DrowsinessModel()
model2.load_state_dict(torch.load(MODEL_PATH_2, map_location=torch.device("cpu")))
model2.eval()

classes = ["normal", "head_tilting", "slow_eye_closure", "yawning"]

# 웹캠 코드처럼 시퀀스(예: window_size=100 프레임)를 모아 예측하기 위한 버퍼와 사이즈
window_size = 100
landmark_buffer = []

def predict_drowsiness(landmarks: list, additional_variable: float = 1.0) -> dict:
    """
    - 매 호출마다 단일 프레임(길이 1434) Landmark를 받음
    - landmark_buffer에 프레임을 쌓다가 window_size(=100) 이상 모이면 모델에 전달
    - 모델1(Transformer 기반)으로 4클래스 예측 -> softmax 확률
    - 모델2에 위 확률 + 추가 변수를 넣어 최종 졸음(이진) 판단
    """
    global landmark_buffer

    # landmarks: 프레임 하나의 Landmarks (길이 1434)
    # 버퍼에 쌓기
    landmark_buffer.append(landmarks)

    # 버퍼가 아직 100프레임이 안 되었다면, 예측 불가능하므로 안내
    if len(landmark_buffer) < window_size:
        return {
            "message": f"Not enough frames for sequence. {len(landmark_buffer)}/{window_size} collected."
        }

    # 버퍼가 window_size보다 길어지면 가장 오래된 프레임을 버림 (슬라이딩 윈도우 방식)
    if len(landmark_buffer) > window_size:
        landmark_buffer.pop(0)

    # 이제 landmark_buffer는 정확히 window_size개의 프레임 데이터가 있음
    # (window_size, 1434) 형태로 만들고 웹캠 코드와 같은 방식으로 정규화
    input_data = np.array(landmark_buffer, dtype=np.float32)  # shape: (100, 1434)
    # axis=0 기준으로 각 차원별 평균/표준편차를 구해 정규화
    input_data = (input_data - np.mean(input_data, axis=0)) / (np.std(input_data, axis=0) + 1e-6)

    # (배치=1, 시퀀스길이=100, 차원=1434)
    input_tensor = torch.tensor(input_data).unsqueeze(0)  # shape: (1, 100, 1434)

    # 모델1로 4클래스 확률 예측
    with torch.no_grad():
        output1 = model1(input_tensor)  # shape: (1, 4)
        probabilities = nn.functional.softmax(output1, dim=1)[0].cpu().numpy()  # shape: (4,)
        predicted_class = int(np.argmax(probabilities))
        predicted_label = classes[predicted_class]
        confidence = float(probabilities[predicted_class])

    # 모델2 입력: (4 + 1)차원 = model1의 확률 4개 + 추가 변수 1개
    input_for_model2 = np.append(probabilities, additional_variable).astype(np.float32)  # shape: (5,)
    input_for_model2 = torch.tensor(input_for_model2).unsqueeze(0)  # shape: (1, 5)

    with torch.no_grad():
        output2 = model2(input_for_model2)  # shape: (1,)
        drowsiness_prob = float(output2.item())
        drowsiness_status = "Drowsy" if drowsiness_prob >= 0.5 else "Alert"

    return {
        "predicted_label": predicted_label,
        "confidence": confidence,
        "drowsiness_status": drowsiness_status,
        "drowsiness_prob": drowsiness_prob
    }
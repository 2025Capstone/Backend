# /ws/drowsiness/landmarks/{session_id} 수정 코드

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import os, pandas as pd, json, traceback
import itertools

websocket_router = APIRouter()

@websocket_router.websocket("/ws/drowsiness/landmarks/{session_id}")
async def websocket_landmarks(websocket: WebSocket, session_id: str):
    await websocket.accept()
    base_dir    = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                               "../../../drowsiness_data"))
    session_dir = os.path.join(base_dir, session_id)
    os.makedirs(session_dir, exist_ok=True)

    all_rows = []
    # 약 10초 분량(30fps 기준 300 프레임)을 하나의 청크로 설정
    chunk_size = 150

    # --- 👇 핵심 수정 부분 (1) ---
    # 파일 번호와 현재 파일에 저장된 청크 수를 추적하는 변수 추가
    file_index = 1
    chunk_count = 0
    # 파일 하나당 30개의 청크를 저장 (300 프레임/청크 * 30 청크 = 9000 프레임 ≈ 5분)
    chunks_per_file = 60

    # 첫 번째 파일 경로를 생성
    csv_path = os.path.join(session_dir, f"landmarks_{file_index:03}.csv")
    print(f"📂 Start saving to: {csv_path}")
    # --- 👆 핵심 수정 부분 (1) ---

    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                print(f"⚠️  JSON decode fail → {data[:50]}...")
                continue

            if msg.get("type") == "ping" or "frame" not in msg:
                continue

            timestamp = msg["timestamp"]
            landmarks = msg["frame"]

            flattened_landmarks = list(itertools.chain.from_iterable(landmarks))
            all_rows.append([timestamp] + flattened_landmarks)

            # 메모리 버퍼(all_rows)가 가득 차면 파일에 추가합니다.
            if len(all_rows) >= chunk_size:
                df = pd.DataFrame(all_rows)
                df.to_csv(csv_path, mode='a', header=False, index=False)

                print(f"✅ Appended {len(all_rows)} rows to {os.path.basename(csv_path)}")
                all_rows.clear()  # 버퍼 비우기

                # --- 👇 핵심 수정 부분 (2) ---
                chunk_count += 1 # 현재 파일에 청크가 하나 더 저장되었음을 기록

                # 현재 파일에 저장된 청크 수가 5분 분량(30개)에 도달하면
                if chunk_count >= chunks_per_file:
                    file_index += 1 # 다음 파일 번호로 증가
                    chunk_count = 0 # 청크 카운터 초기화
                    # 새 파일 경로 생성
                    csv_path = os.path.join(session_dir, f"landmarks_{file_index:03}.csv")
                    print(f"🔄 Switched to new file: {csv_path}")
                # --- 👆 핵심 수정 부분 (2) ---

    except WebSocketDisconnect:
        print(f"🔌 disconnect [{session_id}]")
    except Exception:
        print("❗ unexpected error")
        traceback.print_exc()
    finally:
        # 연결이 끊어지기 직전, 버퍼에 남아있는 데이터를 마지막 파일에 마저 저장합니다.
        if all_rows:
            df = pd.DataFrame(all_rows)
            df.to_csv(csv_path, mode='a', header=False, index=False)
            print(f"✅ Appended final {len(all_rows)} rows to {os.path.basename(csv_path)}")
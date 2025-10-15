from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import os, pandas as pd, json, traceback

websocket_router = APIRouter()

@websocket_router.websocket("/ws/drowsiness/landmarks/{session_id}")
async def websocket_landmarks(websocket: WebSocket, session_id: str):
    await websocket.accept()
    base_dir    = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                               "../../../drowsiness_data"))
    session_dir = os.path.join(base_dir, session_id)
    os.makedirs(session_dir, exist_ok=True)
    print(f"📂 save dir : {session_dir}")

    all_rows = []
    frame_count = 0
    chunk_size = 71700

    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                print(f"⚠️  JSON decode fail → {data[:50]}...")
                continue

            if msg.get("type") == "ping":
                continue

            if "frame" not in msg:
                continue

            timestamp = msg["timestamp"]
            landmarks = msg["frame"]  # landmarks는 478x3 배열

            for landmark_coords in landmarks:
                # [타임스탬프, x, y, z] 형태의 행을 추가
                all_rows.append([timestamp] + landmark_coords)

            frame_count += 1
            if len(all_rows) >= chunk_size:
                # 이제 DataFrame은 4개의 열(timestamp, x, y, z)을 가짐
                df = pd.DataFrame(all_rows)
                # chunk 인덱스는 frame_count 기반으로 유지 가능
                chunk_index = (frame_count // 1000) + 1  # 1000 프레임마다 파일 인덱스 증가
                csv_path = os.path.join(session_dir, f"landmarks_{chunk_index:03}.csv")
                df.to_csv(csv_path, header=False, index=False)
                all_rows.clear()  # 버퍼 비우기

    except WebSocketDisconnect:
        print(f"🔌 disconnect [{session_id}]")
    except Exception:
        print("❗ unexpected error")
        traceback.print_exc()
    finally:
        if all_rows:
            df = pd.DataFrame(all_rows)
            chunk_index = (frame_count // 1000) + 2  # 마지막 파일 인덱스
            csv_path = os.path.join(session_dir, f"landmarks_{chunk_index:03}.csv")
            df.to_csv(csv_path, header=False, index=False)
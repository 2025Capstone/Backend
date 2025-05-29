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

    frame_buffer, frame_count, chunk_size = [], 0, 1000

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

            frame_buffer.append(msg["frame"])
            frame_count += 1
            if frame_count % chunk_size == 0:
                df = pd.DataFrame([v for f in frame_buffer for v in f])
                csv = os.path.join(session_dir, f"landmarks_{frame_count//chunk_size:03}.csv")
                df.to_csv(csv, header=False, index=False)
                frame_buffer.clear()

    except WebSocketDisconnect:
        print(f"🔌 disconnect [{session_id}]")
    except Exception:
        print("❗ unexpected error")
        traceback.print_exc()
    finally:
        if frame_buffer:
            df = pd.DataFrame([v for f in frame_buffer for v in f])
            csv = os.path.join(session_dir,
                               f"landmarks_{(frame_count//chunk_size)+1:03}.csv")
            df.to_csv(csv, header=False, index=False)
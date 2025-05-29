import glob, os
import numpy as np
import pandas as pd
import torch

def merge_landmark_csvs(session_id: str, base_dir: str):
    session_dir = os.path.join(base_dir, session_id)
    csv_files = sorted(glob.glob(os.path.join(session_dir, '*.csv')))
    all_frames = []
    for csv_file in csv_files:
        df = pd.read_csv(csv_file, header=None)
        arr = df.values.reshape(-1, 478, 3)
        all_frames.append(arr)
    if not all_frames:
        raise ValueError(f"No landmark CSVs found for session {session_id}")
    return np.concatenate(all_frames, axis=0)

def make_shard_and_pt(session_id: str, base_dir: str = "drowsiness_data", shard_size: int = 150):
    merged = merge_landmark_csvs(session_id, base_dir)
    session_dir = os.path.join(base_dir, session_id)
    os.makedirs(session_dir, exist_ok=True)

    num_frames, N, C = merged.shape
    shards = []
    for i in range(0, num_frames, shard_size):
        chunk = merged[i:i + shard_size]
        if chunk.shape[0] < shard_size:      # 마지막 조각은 Zero-padding
            pad = np.zeros((shard_size - chunk.shape[0], N, C), dtype=chunk.dtype)
            chunk = np.concatenate([chunk, pad], axis=0)

        shards.append({
            "face_seq": torch.tensor(chunk, dtype=torch.float32),
            "wear_seq": torch.zeros(39, dtype=torch.float32),
            "label"   : torch.tensor(0.,  dtype=torch.float32),
        })

    # Dataset 이 찾을 수 있도록 *_shard_0.pt 로 저장
    pt_path = os.path.join(session_dir, f"{session_id}_shard_0.pt")
    torch.save(shards, pt_path)
    return pt_path
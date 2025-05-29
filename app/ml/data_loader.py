# src/data_loader.py
import os, glob, torch, re
from torch.utils.data import Dataset

class SessionSequenceDataset(Dataset):
    """
    세션별 윈도우를 모아 S(≥2)개씩 시퀀스로 반환
    Args:
      shard_dir : shards 가 모여있는 폴더
      seq_len   : 윈도우 몇 개를 한 시퀀스로 묶을지
      stride    : 슬라이딩 보폭(윈도우 수)
    """
    _pat = re.compile(r'(.+?)_shard_\d+\.pt')   # session id 추출용

    def __init__(self, shard_dir, seq_len=12, stride=3):
        self.seq_len = seq_len
        self.stride  = stride

        # --- 1) 세션별 윈도우 로드 ---
        sessions = {}  # {session_id: [dict, ...]}
        for path in sorted(glob.glob(os.path.join(shard_dir, '*_shard_*.pt'))):
            sess_id = self._pat.match(os.path.basename(path)).group(1)
            windows = torch.load(path)  # list of dicts
            sessions.setdefault(sess_id, []).extend(windows)

        # --- 2) 세션 내부 슬라이딩 인덱스 구성 ---
        self.index_map = []  # [(sess_id, start_idx)]
        for sid, win_list in sessions.items():
            n = len(win_list)
            for s in range(0, n - seq_len + 1, stride):
                self.index_map.append((sid, s))
        self.sessions = sessions  # keep

    def __len__(self):
        return len(self.index_map)

    def __getitem__(self, idx):
        sid, start = self.index_map[idx]
        wins = self.sessions[sid][start : start + self.seq_len]   # list length S
        # stack: face → [S, T, N, 3], wear → [S, 36], label → [S] (혹은 마지막)
        face = torch.stack([w['face_seq'] for w in wins])  # [S,T,N,3]
        wear = torch.stack([w['wear_seq'] for w in wins])  # [S,36]
        label= wins[-1]['label'].float()                   # scalar(1,) → 회귀타깃
        return face, wear, label

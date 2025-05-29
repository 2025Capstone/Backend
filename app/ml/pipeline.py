from .face_GNN import FaceSTGCNModel   # assume saved separately
from .hrv_embedding import HRVFeatureEmbedder
from .fusion import MLPFusion, ConvAggregation, ElementwiseFusion, OrdinalHead
from .fusion import TemporalBiLSTM, RegressionHead
import torch
import torch.nn as nn
from typing import Tuple, Optional


class MultimodalFatigueModel(nn.Module):
    def __init__(self, num_classes: int = 5):
        super().__init__()
        self.face_embed = FaceSTGCNModel()
        self.hrv_embed = HRVFeatureEmbedder()
        # fusion
        self.mlp_fusion = MLPFusion()
        self.conv_aggr = ConvAggregation()
        self.elem_fusion = ElementwiseFusion()
        # temporal
        self.temporal = TemporalBiLSTM()
        self.regressor = RegressionHead(self.temporal.output_dim)

    def forward(self,
                face_seq: torch.Tensor,
                hrv_seq: torch.Tensor,
                edge_index: torch.Tensor) -> Tuple[torch.Tensor, dict]:

        B, S, T, N, C = face_seq.shape  # S=12 windows of 150 frames

        # reshape to process each 5‑s window independently through ST‑GCN
        face_seq_reshaped = face_seq.view(B * S, T, N, C)
        hrv_seq_reshaped = hrv_seq.view(B * S, -1)  # [B*S, 36]

        hF = self.face_embed(face_seq_reshaped, edge_index)          # [B*S, 64]
        hP = self.hrv_embed(hrv_seq_reshaped)                        # [B*S, 64]

        # RBM‑like stage (simplified)
        H = self.mlp_fusion(hF, hP)                                  # complementary feat 64
        hF_aggr, hP_aggr, f = self.conv_aggr(hF, hP)                 # aggregated feat 64
        F_fused = self.elem_fusion(H, f)                             # final fused feat 64

        # pack back to sequence
        seq_feat = F_fused.view(B, S, -1)                            # [B, 12, 64]

        temporal_out = self.temporal(seq_feat)                       # [B, D]
        fatigue_pred = self.regressor(temporal_out)                  # [B, 1]

        aux = {
            'H': H.detach(),     # [B*S, 64]
            'f': f.detach(),
            'F': F_fused.detach()
        }
        return fatigue_pred, aux

import torch
import torch.nn as nn

class MLPFusion(nn.Module):
    def __init__(self, input_dim: int = 128, hidden_dim: int = 64, output_dim: int = 64):
        super(MLPFusion, self).__init__()
        self.mlp = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(inplace=True),
            nn.Linear(hidden_dim, output_dim),
            nn.ReLU(inplace=True)
        )

    def forward(self, hF: torch.Tensor, hP: torch.Tensor) -> torch.Tensor:
        x = torch.cat([hF, hP], dim=-1)
        H = self.mlp(x)
        return H


class ConvAggregation(nn.Module):
    def __init__(self, feat_dim: int = 64, fusion_dim: int = 64):
        super(ConvAggregation, self).__init__()
        self.convF = nn.Sequential(
            nn.Linear(feat_dim, feat_dim),
            nn.ReLU(inplace=True)
        )
        self.convP = nn.Sequential(
            nn.Linear(feat_dim, feat_dim),
            nn.ReLU(inplace=True)
        )
        self.convFuse = nn.Sequential(
            nn.Linear(feat_dim * 2, fusion_dim),
            nn.ReLU(inplace=True)
        )

    def forward(self, hF: torch.Tensor, hP: torch.Tensor):
        hF_out = self.convF(hF)
        hP_out = self.convP(hP)
        concat = torch.cat([hF_out, hP_out], dim=-1)
        f = self.convFuse(concat)
        return hF_out, hP_out, f
    
    
class ElementwiseFusion(nn.Module):
    def __init__(self):
        super(ElementwiseFusion, self).__init__()

    def forward(self, H: torch.Tensor, f: torch.Tensor) -> torch.Tensor:
        assert H.shape == f.shape
        F = H * f
        return F


class TemporalBiLSTM(nn.Module):
    def __init__(self, input_dim: int = 64, hidden_dim: int = 128, num_layers: int = 1, bidirectional: bool = True):
        super(TemporalBiLSTM, self).__init__()
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            bidirectional=bidirectional
        )
        self.output_dim = hidden_dim * (2 if bidirectional else 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        outputs, _ = self.lstm(x)
        last_forward = outputs[:, -1, :self.lstm.hidden_size]
        last_backward = outputs[:, 0, self.lstm.hidden_size:]
        last = torch.cat([last_forward, last_backward], dim=-1)
        return last

class RegressionHead(nn.Module):
    def __init__(self, input_dim: int):
        super(RegressionHead, self).__init__()
        self.fc = nn.Sequential(
            nn.Linear(input_dim, input_dim // 2),
            nn.ReLU(inplace=True),
            nn.Linear(input_dim // 2, 1),
            nn.Sigmoid()
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.fc(x) * 4 + 1 # [1, 5]



class OrdinalHead(nn.Module):
    """
    CORAL/CORN: num_classes-1개의 logit 출력 (sigmoid는 Loss에서 처리)
    """
    def __init__(self, in_dim: int, num_classes: int = 5):
        super().__init__()
        self.fc = nn.Linear(in_dim, num_classes - 1)  # 4 logits

    def forward(self, x):                     # x: [B, in_dim]
        return self.fc(x)
import torch
import torch.nn as nn

class HRVFeatureEmbedder(nn.Module):
    def __init__(self, input_dim=39, embed_dim=64, hidden_dim=48):
        super(HRVFeatureEmbedder, self).__init__()
        self.network = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(inplace=True),
            nn.Linear(hidden_dim, embed_dim),
            nn.ReLU(inplace=True)
        )

    def forward(self, x):
        return self.network(x)

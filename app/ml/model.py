import torch
import torch.nn as nn
from torch.nn import TransformerEncoder, TransformerEncoderLayer


class FaceLandmarksModelAttention(nn.Module):
    def __init__(self, input_dim=1434, hidden_size=128, num_classes=4, num_heads=4, num_layers=2):
        super(FaceLandmarksModelAttention, self).__init__()
        self.embedding = nn.Linear(input_dim, hidden_size)
        self.transformer = TransformerEncoder(
            TransformerEncoderLayer(hidden_size, num_heads, dim_feedforward=256, dropout=0.1, batch_first=True),
            num_layers
        )
        self.fc1 = nn.Linear(hidden_size, 64)
        self.fc2 = nn.Linear(64, num_classes)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(0.5)

    def forward(self, x):
        x = self.embedding(x)
        x = self.transformer(x)
        x = x.mean(dim=1)
        x = self.dropout(self.relu(self.fc1(x)))
        out = self.fc2(x)
        return out

class DrowsinessModel(nn.Module):
    def __init__(self, input_size=5):
        super(DrowsinessModel, self).__init__()
        self.fc1 = nn.Linear(input_size, 16)
        self.relu1 = nn.ReLU()
        self.fc2 = nn.Linear(16, 8)
        self.relu2 = nn.ReLU()
        self.fc3 = nn.Linear(8, 1)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        x = self.relu1(self.fc1(x))
        x = self.relu2(self.fc2(x))
        x = self.sigmoid(self.fc3(x))
        return x
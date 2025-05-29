import torch
import torch.nn as nn
from torch_geometric.nn import GCNConv

class STGCNBlock(nn.Module):
    def __init__(self, in_channels, out_channels):
        super(STGCNBlock, self).__init__()
        self.gcn1 = GCNConv(in_channels, out_channels)
        self.relu = nn.ReLU()
        self.gcn2 = GCNConv(out_channels, out_channels)

    def forward(self, x, edge_index):
        x = self.gcn1(x, edge_index)
        x = self.relu(x)
        x = self.gcn2(x, edge_index)
        x = self.relu(x)
        return x

class TemporalConvNet(nn.Module):
    def __init__(self, in_channels, num_channels, kernel_size=2, dropout=0.2):
        super(TemporalConvNet, self).__init__()
        layers = []
        for i in range(len(num_channels)):
            dilation_size = 2 ** i
            in_ch = in_channels if i == 0 else num_channels[i-1]
            out_ch = num_channels[i]
            layers += [
                nn.Conv1d(in_ch, out_ch, kernel_size, stride=1,
                          dilation=dilation_size, padding=(kernel_size-1)*dilation_size),
                nn.ReLU(),
                nn.Dropout(dropout)
            ]
        self.network = nn.Sequential(*layers)

    def forward(self, x):
        return self.network(x)

class FaceSTGCNModel(nn.Module):
    def __init__(self, in_channels=3, gcn_out=64, tcn_channels=[64,128]):
        super(FaceSTGCNModel, self).__init__()
        self.stgcn = STGCNBlock(in_channels, gcn_out)
        self.tcn = TemporalConvNet(gcn_out, tcn_channels)
        self.pool = nn.AdaptiveAvgPool1d(1)
        self.final_dim = tcn_channels[-1]
        self.projection = nn.Linear(self.final_dim, 64)

    def forward(self, x, edge_index):
        batch, T, num_nodes, in_ch = x.shape # T는 처리하는 프레임 수
        x = x.view(batch * T, num_nodes, in_ch)
        x = x.view(-1, in_ch)
        x = self.stgcn(x, edge_index)
        x = x.view(batch, T, num_nodes, -1).mean(2)
        x = x.permute(0, 2, 1)
        x = self.tcn(x)
        x = self.pool(x).squeeze(-1)
        x = self.projection(x)
        return x # 출력 임베딩 크기는 64
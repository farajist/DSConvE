import torch.nn as nn
import torch
import torch.nn.functional as F


class Flatten(nn.Module):
    def forward(self, x):
        n, _, _, _ = x.size()
        x = x.view(n, -1)
        return x

class DSConv2d(nn.Module):
    def __init__(self, in_channels, out_channels, kernel_size = 3, padding = 1, bias=False):
        super(DSConv2d, self).__init__()
        self.depthwise = nn.Conv2d(in_channels, in_channels, kernel_size=kernel_size, padding=padding, groups=in_channels, bias=bias)
        self.pointwise = nn.Conv2d(in_channels, out_channels, kernel_size=1, bias=bias)

    def forward(self, x):
        out = self.depthwise(x)
        out = self.pointwise(out)
        return out

class DSConvE(nn.Module):
    def __init__(self, num_e, num_r, embedding_size_h=20, embedding_size_w=10,
                 conv_channels=32, conv_kernel_size=3, embed_dropout=0.2, feature_map_dropout=0.2,
                 proj_layer_dropout=0.3):
        super().__init__()

        self.num_e = num_e
        self.num_r = num_r
        self.embedding_size_h = embedding_size_h
        self.embedding_size_w = embedding_size_w

        embedding_size = embedding_size_h * embedding_size_w
        flattened_size = (embedding_size_w * 2 - conv_kernel_size + 1) * \
                         (embedding_size_h - conv_kernel_size + 1) * conv_channels

        self.embed_e = nn.Embedding(num_embeddings=self.num_e, embedding_dim=embedding_size)
        self.embed_r = nn.Embedding(num_embeddings=self.num_r, embedding_dim=embedding_size)

        self.conv_e = nn.Sequential(
            nn.Dropout(p=embed_dropout),
            DSConv2d(in_channels=1, out_channels=conv_channels, kernel_size=conv_kernel_size, padding=0),
            nn.ReLU(),
            nn.BatchNorm2d(num_features=conv_channels),
            nn.Dropout2d(p=feature_map_dropout),

            Flatten(),
            nn.Linear(in_features=flattened_size, out_features=embedding_size),
            nn.ReLU(),
            nn.BatchNorm1d(num_features=embedding_size),
            nn.Dropout(p=proj_layer_dropout)
        )

    def forward(self, s, r):
        embed_s = self.embed_e(s)
        embed_r = self.embed_r(r)

        embed_s = embed_s.view(-1, self.embedding_size_w, self.embedding_size_h)
        embed_r = embed_r.view(-1, self.embedding_size_w, self.embedding_size_h)
        conv_input = torch.cat([embed_s, embed_r], dim=1).unsqueeze(1)
        out = self.conv_e(conv_input)

        scores = out.mm(self.embed_e.weight.t())

        return scores

    def test(self, s, r):
        return F.sigmoid(self(s, r))

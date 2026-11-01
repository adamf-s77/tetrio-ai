"""
cnn_evaluator.py
CNN 模型載入與盤面評估 (Value 與 Variance)
"""

import os
import sys
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


def state_to_tensor(board):
    """將 20 行 bitmask 轉為 (1, 1, 22, 10) 的 Tensor"""
    grid = np.zeros((1, 1, 22, 10), dtype=np.float32)
    for r in range(min(len(board), 20)):
        row_val = board[r]
        if row_val:
            for c in range(10):
                if (row_val >> (9 - c)) & 1:
                    grid[0, 0, r, c] = 1.0
    return torch.from_numpy(grid)


def states_to_batch_tensor(boards):
    """批次盤面轉 Tensor"""
    b_size = len(boards)
    grid = np.zeros((b_size, 1, 22, 10), dtype=np.float32)
    for i, board in enumerate(boards):
        for r in range(min(len(board), 20)):
            row_val = board[r]
            if row_val:
                for c in range(10):
                    if (row_val >> (9 - c)) & 1:
                        grid[i, 0, r, c] = 1.0
    return torch.from_numpy(grid)


class TetrisValueVarianceNet(nn.Module):
    """雙頭 (Value / Variance) CNN 模型"""

    def __init__(self):
        super().__init__()
        self.conv1 = nn.Conv2d(1, 32, kernel_size=3, stride=1)
        self.bn1 = nn.BatchNorm2d(32)
        self.conv2 = nn.Conv2d(32, 32, kernel_size=3, stride=1)
        self.bn2 = nn.BatchNorm2d(32)

        self.fc1 = nn.Linear(3456, 128)
        self.fc_v = nn.Linear(128, 1)      # Value Head
        self.fc_var = nn.Linear(128, 1)    # Variance Head

    def forward(self, x):
        x = F.relu(self.conv1(x))
        x = F.relu(self.conv2(x))
        x = x.view(x.shape[0], -1)
        x = F.relu(self.fc1(x))

        value = self.fc_v(x)
        var = F.relu(self.fc_var(x)) + 1e-4
        return value, var


class CNNPolicyEvaluator:
    """載入 checkpoint 並提供 evaluate() 介面"""

    DEFAULT_CHECKPOINT_PATHS = [
        os.path.join(os.path.dirname(os.path.dirname(__file__)), 'results', 'online-200sims', 'model_checkpoint'),
        os.path.join('results', 'online-200sims', 'model_checkpoint'),
        os.path.join('pytorch_model', 'model_checkpoint'),
    ]

    def __init__(self, model_path=None, device=None):
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = TetrisValueVarianceNet().to(self.device)
        self.is_loaded = False
        self.model_path = None

        target_path = model_path
        if target_path is None:
            for p in self.DEFAULT_CHECKPOINT_PATHS:
                if os.path.isfile(p):
                    target_path = p
                    break

        if target_path and os.path.isfile(target_path):
            try:
                checkpoint = torch.load(target_path, map_location=self.device)
                state_dict = checkpoint.get('model_state_dict', checkpoint)
                self.model.load_state_dict(state_dict)
                self.model.eval()
                self.is_loaded = True
                self.model_path = target_path
                print(f"載入模型權重: {target_path} ({self.device})")
            except Exception as e:
                print(f"權重載入失敗 ({e})，使用隨機初始化。")
                self.model.eval()
        else:
            print("未找到權重檔案，使用隨機初始化。")
            self.model.eval()

    def evaluate(self, board):
        x = state_to_tensor(board).to(self.device)
        with torch.no_grad():
            val, var = self.model(x)
        return float(val.item()), float(var.item())

    def evaluate_batch(self, boards):
        if not boards:
            return [], []
        x = states_to_batch_tensor(boards).to(self.device)
        with torch.no_grad():
            vals, vars_ = self.model(x)
        return vals.squeeze(-1).cpu().numpy().tolist(), vars_.squeeze(-1).cpu().numpy().tolist()

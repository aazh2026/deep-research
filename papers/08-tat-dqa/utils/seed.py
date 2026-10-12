"""随机种子工具。"""

import random
import os

import numpy as np
import torch


def set_seed(seed: int = 42) -> None:
    """设置 Python、NumPy、PyTorch 的随机状态，保证可复现性。"""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    # macOS CPU 不需要 CUDA 设置
    os.environ["PYTHONHASHSEED"] = str(seed)
    # 抑制 HuggingFace datasets 的多 worker 警告
    os.environ["TOKENIZERS_PARALLELISM"] = "false"


def get_device() -> torch.device:
    """返回可用设备（优先 CUDA，否则 MPS，最后 CPU）。"""
    if torch.cuda.is_available():
        return torch.device("cuda")
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")
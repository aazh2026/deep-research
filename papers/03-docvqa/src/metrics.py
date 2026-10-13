"""DocVQA ANLS（Average Normalized Levenshtein Similarity）官方实现。

论文：Mathew et al. "DocVQA: A Dataset for VQA on Document Images" (WACV 2021)
原始公式来源：Biten et al. "ICDAR 2019 Competition on Scene Text VQA" (ICCV 2019)
官方实现参考：https://github.com/aimagelab/ST-VQA

公式（τ = 0.5）：
    NED(a, â) = edit_distance(a, â) / max(|a|, |â|)
    S(a, â)   = 1 - NED  if NED < τ
              = 0         otherwise
    ANLS      = mean over Q of max(S over all gold answers)

关键设计点：
- 预归一化 lowercase + strip
- 多 gold 取 max（处理标注者分歧）
- 空 + 空 → 1.0（防除零）
- NED >= τ → 0（区分「轻微 OCR 错」vs「完全错」）
"""

from __future__ import annotations

import editdistance


def levenshtein(s1: str, s2: str) -> int:
    """Levenshtein 编辑距离（字符级）。"""
    return editdistance.eval(s1, s2)


def anls_score(prediction: str, ground_truths: list[str],
               tau: float = 0.5) -> float:
    """单题 ANLS 分数。

    参数：
    - prediction: 预测字符串
    - ground_truths: 该题所有可接受 gold 答案（标注者可能给多个）
    - tau: NED 阈值；>= tau 给 0 分

    返回：max similarity across all ground truths in [0, 1]
    """
    pred = prediction.lower().strip()
    best = 0.0
    for gt in ground_truths:
        gt = gt.lower().strip()
        # 空 + 空 视为完美匹配
        if not pred and not gt:
            return 1.0
        if not pred or not gt:
            # 一个空一个非空：NED=1（如果 max(len) 非零），给 0
            continue
        d = levenshtein(pred, gt)
        nld = d / max(len(pred), len(gt))
        if nld < tau:
            score = 1.0 - nld
            if score > best:
                best = score
    return best


def anls_dataset(predictions: list[str],
                 ground_truths_list: list[list[str]],
                 tau: float = 0.5) -> dict:
    """整个数据集的 ANLS。

    返回：{"anls": float, "n": int, "scores": list[float]}
    """
    assert len(predictions) == len(ground_truths_list), \
        f"predictions ({len(predictions)}) 与 ground_truths_list ({len(ground_truths_list)}) 长度不一致"
    scores = [
        anls_score(p, gts, tau)
        for p, gts in zip(predictions, ground_truths_list)
    ]
    n = len(scores)
    return {
        "anls": sum(scores) / n if n else 0.0,
        "n": n,
        "scores": scores,
    }

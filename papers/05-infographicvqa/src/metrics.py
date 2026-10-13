"""InfographicVQA ANLS metric（与 03-docvqa 共用公式）。

Paper: Mathew et al. "InfographicVQA" (WACV 2022)
公式来源：与 DocVQA Challenge 2020 (arXiv:2008.08899) 一致
       NED = edit_distance / max(|a|, |b|)
       S = 1 - NED if NED < τ else 0
       ANLS = mean over Q of max(S over all gold answers)
       τ = 0.5
"""

from __future__ import annotations

import editdistance


def levenshtein(s1: str, s2: str) -> int:
    return editdistance.eval(s1, s2)


def anls_score(prediction: str, ground_truths: list[str], tau: float = 0.5) -> float:
    pred = prediction.lower().strip()
    best = 0.0
    for gt in ground_truths:
        gt = gt.lower().strip()
        if not pred and not gt:
            return 1.0
        if not pred or not gt:
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
    assert len(predictions) == len(ground_truths_list)
    scores = [
        anls_score(p, gts, tau)
        for p, gts in zip(predictions, ground_truths_list)
    ]
    n = len(scores)
    return {"anls": sum(scores) / n if n else 0.0, "n": n, "scores": scores}

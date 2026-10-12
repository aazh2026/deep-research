"""TAT-DQA 字段解析与规范化。

数据集来源：Hugging Face `next-tat/TAT-DQA`
字段映射：
- question: str
- answer / answers: 答案（形式随 answer_type 而变）
- answer_type: str ∈ {span, multi-span, count, arithmetic}
- scale: str ∈ {'', thousand, million, billion, percent}
- derivation: str（仅 arithmetic 类型）
- facts: list[str]
- table / text: str（文档片段）
- block_mapping: dict

本模块负责把 HuggingFace 原始样本规整为统一的 TATSample 数据类。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

from utils.decode import ANSWER_TYPE2ID, OP2ID, SCALE2ID, sanitize_expression


@dataclass
class TATSample:
    """统一后的 TAT-DQA 样本。"""

    uid: str
    question: str
    context: str                  # 拼接后的 context 文本
    answer: Any                   # str | list[str] | int | float
    answer_type: str              # span / multi-span / count / arithmetic
    answer_type_id: int           # 0-3
    scale: str                    # '' / thousand / ...
    scale_id: int                 # 0-4
    derivation: str               # 算式（已 sanitize）
    facts: list[str] = field(default_factory=list)
    span_start: int = -1          # gold span 起始 token（col-major index in context）
    span_end: int = -1            # gold span 结束 token（inclusive）
    tag_labels: list[int] = field(default_factory=list)  # BIO 标签，按 context 长度
    arith_op: int = -1            # 主要运算符 id
    arith_count: int = 0          # 操作数数量

    def to_dict(self) -> dict:
        return {
            "uid": self.uid,
            "question": self.question,
            "context": self.context,
            "answer": self.answer,
            "answer_type": self.answer_type,
            "answer_type_id": self.answer_type_id,
            "scale": self.scale,
            "scale_id": self.scale_id,
            "derivation": self.derivation,
            "facts": self.facts,
            "span_start": self.span_start,
            "span_end": self.span_end,
            "tag_labels": self.tag_labels,
            "arith_op": self.arith_op,
            "arith_count": self.arith_count,
        }


def _normalize_answer_type(raw: Any) -> str:
    """规整 answer_type 字段名。"""
    if raw is None:
        return "span"
    s = str(raw).strip().lower()
    # 多种命名形式
    if s in ("span", "spans", "single-span", "single_span"):
        return "span" if s != "spans" else "multi-span"
    if s in ("multi-span", "multispan", "multi_span", "spans"):
        return "multi-span"
    if s in ("count", "counting", "counter"):
        return "count"
    if s in ("arithmetic", "arith", "math", "numerical"):
        return "arithmetic"
    return "span"  # 默认


def _normalize_scale(raw: Any) -> str:
    """规整 scale 字段。"""
    if raw is None:
        return ""
    s = str(raw).strip().lower()
    if s in ("", "none", "null", "no"):
        return ""
    if "thousand" in s:
        return "thousand"
    if "million" in s:
        return "million"
    if "billion" in s:
        return "billion"
    if "percent" in s or s == "%":
        return "percent"
    return ""


def _extract_answer(raw: Any) -> Any:
    """提取答案原值。"""
    if raw is None:
        return ""
    if isinstance(raw, (int, float)):
        return raw
    if isinstance(raw, str):
        return raw.strip()
    if isinstance(raw, list):
        return [_extract_answer(x) for x in raw]
    if isinstance(raw, dict):
        # 部分格式：{"answer": ..., "answer_type": ...}
        return raw.get("answer", raw.get("text", ""))
    return str(raw).strip()


def _build_context(text: str, table: str, facts: list[str], max_len: int = 4000) -> str:
    """拼接 context：优先用 facts，没有再退到 table + text。"""
    parts = []
    if facts and len(facts) > 0:
        # facts 是最相关的 evidence 段
        parts.append("EVIDENCE: " + " | ".join(str(f) for f in facts))
    if table:
        parts.append("TABLE: " + table[:1500])
    if text:
        parts.append("TEXT: " + text[:1500])
    ctx = "\n".join(parts)
    if len(ctx) > max_len:
        ctx = ctx[:max_len]
    return ctx


def _extract_main_op(derivation: str) -> int:
    """从算式中提取最主要的运算符。"""
    cleaned = sanitize_expression(derivation)
    # 按出现顺序遍历
    for ch in cleaned:
        if ch == "+":
            return OP2ID["+"]
        if ch == "-":
            return OP2ID["-"]
        if ch == "*":
            return OP2ID["*"]
        if ch == "/":
            return OP2ID["/"]
    return -1  # 无运算符


def _count_numbers(derivation: str) -> int:
    cleaned = sanitize_expression(derivation)
    return len(re.findall(r"\d+\.?\d*", cleaned))


def parse_raw_sample(raw: dict) -> Optional[TATSample]:
    """把 HuggingFace 原始 dict 转成 TATSample。"""
    try:
        question = (raw.get("question") or "").strip()
        if not question:
            return None

        answer_type = _normalize_answer_type(raw.get("answer_type"))
        answer_type_id = ANSWER_TYPE2ID[answer_type]
        scale = _normalize_scale(raw.get("scale"))
        scale_id = SCALE2ID.get(scale, 0)
        answer = _extract_answer(raw.get("answer") or raw.get("answers"))

        text = raw.get("text") or ""
        table = raw.get("table") or ""
        facts = raw.get("facts") or []
        if isinstance(facts, str):
            facts = [facts]
        derivation = sanitize_expression(raw.get("derivation") or "")

        context = _build_context(text, table, facts)

        uid = raw.get("uid") or raw.get("id") or raw.get("doc", {}).get("uid", "")
        if isinstance(raw.get("doc"), dict):
            uid = raw["doc"].get("uid", uid)

        arith_op = _extract_main_op(derivation) if answer_type == "arithmetic" else -1
        arith_count = _count_numbers(derivation) if answer_type == "arithmetic" else 0

        return TATSample(
            uid=str(uid),
            question=question,
            context=context,
            answer=answer,
            answer_type=answer_type,
            answer_type_id=answer_type_id,
            scale=scale,
            scale_id=scale_id,
            derivation=derivation,
            facts=facts,
            arith_op=arith_op,
            arith_count=arith_count,
        )
    except Exception as e:
        print(f"[parse_raw_sample] 跳过异常样本: {e}")
        return None


def load_hf_samples(
    hf_dataset_name: str = "next-tat/TAT-DQA",
    cache_dir: str = "./cache",
    split: str = "train",
    max_samples: Optional[int] = None,
    local_dir: Optional[str] = None,
) -> list[TATSample]:
    """加载 TAT-DQA 样本。

    数据源：
    - 若提供 ``local_dir``（含 tatdqa_dataset_{split}.json），从本地读取
    - 否则从 HuggingFace ``next-tat/TAT-DQA`` 加载（注意：HF 上 train/val 是图片格式，仅 test 是 JSON）
    """
    if local_dir is not None:
        return load_local_samples(local_dir=local_dir, split=split, max_samples=max_samples)

    from datasets import load_dataset

    ds = load_dataset(hf_dataset_name, cache_dir=cache_dir, split=split)
    samples = []
    for i, raw in enumerate(ds):
        if max_samples is not None and i >= max_samples:
            break
        s = parse_raw_sample(dict(raw))
        if s is not None and s.context:
            samples.append(s)
    return samples


def load_local_samples(
    local_dir: str = "./data_local",
    split: str = "train",
    max_samples: Optional[int] = None,
) -> list[TATSample]:
    """从 fengbinzhu/TAT-LLM 的 JSON 文件加载。

    数据结构：每个顶层 item = {doc: {uid, page, source}, questions: [QuestionDict, ...]}。
    每条 question 展开成一条 TATSample。
    """
    import json
    import os

    split_to_file = {
        "train": "tatdqa_dataset_train.json",
        "validation": "tatdqa_dataset_dev.json",
        "dev": "tatdqa_dataset_dev.json",
        "test": "tatdqa_dataset_test.json",
    }
    fname = split_to_file.get(split)
    if fname is None:
        raise ValueError(f"未知 split: {split}")
    path = os.path.join(local_dir, fname)
    if not os.path.exists(path):
        raise FileNotFoundError(f"找不到数据文件: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    samples: list[TATSample] = []
    for doc in data:
        doc_uid = doc.get("doc", {}).get("uid", "")
        for q in doc.get("questions", []):
            # 把 doc 信息注入 q，让 parse_raw_sample 看到
            merged = {**q, "doc": doc.get("doc", {})}
            s = parse_raw_sample(merged)
            if s is not None and s.context:
                if not s.uid:
                    s.uid = f"{doc_uid}_{q.get('uid', '')}"
                samples.append(s)
                if max_samples is not None and len(samples) >= max_samples:
                    return samples
    return samples
"""PDF 文本提取 + 答案可检索性分析。

SynthDocBench 的 paper baseline (Fig 5) 对比：
- Vision-only VLM（看图）
- OCR + GPT-4o（看 PyMuPDF 抽出的文本）

我们要回答的核心问题是：「chart 类型的问题需要 vision 吗？」

代理实验：
- 对每道问题，把 gold answer 拿到 PDF 抽出的文本里搜
- 如果 hit → text-only 可能能做对（即使要 context）
- 如果 miss → 答案仅在视觉里（D3.js 图表的数据点），text-only 不可能做对

这是 paper claim 的 "complex subset 用 OCR 反而比 vision 强 (0.798 vs 0.360)，
但 chart subset 用 OCR 大跌 (0.297 vs 0.457)" 的底层数据解释。
"""

from __future__ import annotations

import json
import os
import re
import string
from typing import Optional

import pymupdf


# 用于「文本里的数字」与「gold 答案里的数字」比较
NUM_RE = re.compile(r"-?\d[\d,]*(?:\.\d+)?%?")


def download_pdf(pdf_filename: str, save_dir: str = "./data/pdfs",
                 cache_dir: str = "./cache") -> str:
    """从 HF 下载单个 PDF，返回本地路径。"""
    os.makedirs(save_dir, exist_ok=True)
    local = os.path.join(save_dir, os.path.basename(pdf_filename))
    if os.path.exists(local):
        return local
    print(f"[pdf] 下载 {pdf_filename[:60]}...")
    from huggingface_hub import hf_hub_download
    path = hf_hub_download(
        repo_id="ServiceNow-AI/SynthDocBench",
        repo_type="dataset",
        filename=f"pdfs/{pdf_filename}",
        cache_dir=cache_dir,
        local_dir=save_dir,
    )
    return path


def extract_pdf_text(pdf_path: str, max_chars: int | None = None) -> str:
    """提取 PDF 全文（PyMuPDF）。"""
    doc = pymupdf.open(pdf_path)
    out: list[str] = []
    total = 0
    for page in doc:
        text = page.get_text()
        if max_chars is not None and total + len(text) > max_chars:
            text = text[: max(0, max_chars - total)]
        out.append(text)
        total += len(text)
        if max_chars is not None and total >= max_chars:
            break
    doc.close()
    return "\n".join(out)


def extract_pdf_pages(pdf_path: str) -> list[str]:
    """返回每页文本的列表。"""
    doc = pymupdf.open(pdf_path)
    pages = [p.get_text() for p in doc]
    doc.close()
    return pages


def normalize_text(s: str) -> str:
    """文本归一化（小写、压缩空白、去掉标点）用于子串匹配。"""
    s = s.lower()
    s = re.sub(r"\s+", " ", s)
    return s


def extract_numbers(text: str) -> list[str]:
    """从文本里抽所有数字 token（含千分位 + 百分号 + 小数）。"""
    return NUM_RE.findall(text)


def find_answer_in_text(
    gold_answer: str,
    pdf_text: str,
    pdf_pages: list[str] | None = None,
) -> dict:
    """判断 gold answer 在 PDF 文本里是否「可定位到」。

    判定策略：
    1. 直接子串匹配（normalized）
    2. gold 答案里的关键数字是否在 PDF 文本里出现
    3. 关键短语（>3 字符的非停用词）是否有任何一个出现在 PDF 里

    返回：{
      "substring_hit": bool,
      "number_hits": int / total_numbers,
      "key_phrase_hits": int / total_phrases,
      "evidence_page": Optional[int],   # 若有页码定位
    }
    """
    norm_gold = normalize_text(gold_answer)
    norm_text = normalize_text(pdf_text)
    substring_hit = norm_gold in norm_text

    # 数字 hit
    nums = extract_numbers(gold_answer)
    num_hits = 0
    for n in nums:
        if n.lower() in norm_text:
            num_hits += 1
    num_total = len(nums)

    # 关键短语 hit：取 gold answer 里 5+ 字符的「英文词」
    key_phrases = re.findall(r"[a-z]{5,}", gold_answer.lower())
    # 去掉常见停用词
    STOP = {"about", "which", "these", "those", "where", "there", "their",
            "would", "could", "should", "between", "across", "however",
            "because", "although", "include", "including", "according"}
    key_phrases = [p for p in key_phrases if p not in STOP]
    if key_phrases:
        phrase_hits = sum(1 for p in key_phrases if p in norm_text)
    else:
        phrase_hits = 0
    phrase_total = len(key_phrases)

    # 找页码（substring 命中 → 精确定位；否则退到第一个 number 所在页）
    evidence_page: int | None = None
    if pdf_pages:
        if substring_hit:
            for i, page_text in enumerate(pdf_pages):
                if norm_gold in normalize_text(page_text):
                    evidence_page = i
                    break
        # 如果 substring miss 但有 number hit，定位到第一个 number 页
        if evidence_page is None and num_hits > 0 and nums:
            target = nums[0].lower()
            for i, page_text in enumerate(pdf_pages):
                if target in normalize_text(page_text):
                    evidence_page = i
                    break

    return {
        "substring_hit": substring_hit,
        "num_hits": num_hits,
        "num_total": num_total,
        "phrase_hits": phrase_hits,
        "phrase_total": phrase_total,
        "evidence_page": evidence_page,
        # 综合判定：「text-only 可能答得出」= 有任何一种 hit
        "any_hit": substring_hit or num_hits > 0 or phrase_hits > 0,
    }

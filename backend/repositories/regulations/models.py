"""法规库的数据契约 —— Day 1 of v0.1.0.

每条 regulation 来自 seed.yaml；keyword search 命中时返回 SearchHit
（轻量结构，不含 full_text，节省 prompt token）；agent 通过
``get_regulation(id)`` 才读完整条款。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

# 4 个分类对应 PRD §6.1 法规来源
RegulationCategory = Literal["VAT", "CIT", "IIT", "CAS"]
ALLOWED_CATEGORIES: tuple[RegulationCategory, ...] = ("VAT", "CIT", "IIT", "CAS")


@dataclass(frozen=True)
class Regulation:
    """种子库的一条条款，从 seed.yaml 加载."""

    id: str
    category: RegulationCategory
    source_name: str
    source_url: str
    chapter: str
    article_number: str
    title: str
    summary: str
    full_text: str
    tags: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SearchHit:
    """keyword_search 返回的轻量结构 —— 不含 full_text 节省 prompt token."""

    id: str
    title: str
    summary: str
    source_name: str
    score: float  # 归一化 [0, 1]

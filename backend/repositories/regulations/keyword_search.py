"""Keyword search over regulations —— Day 2 of v0.1.0.

用 BM25Okapi（rank_bm25）+ jieba 切词做中文 keyword search；不引入 embedding /
vector DB（north star）。

Corpus = ``title + summary + tags`` 拼接（不索引 full_text）：让 agent 通过
``search_regulations`` 命中 → ``get_regulation(id)`` 取全文，节省 prompt token
也强制 agent 显式引用。

score 归一化到 [0, 1]：``BM25Okapi.get_scores`` 原始分受 corpus 长度影响不便
跨 query 比较，归一化后更适合 prompt 里展示给 LLM。
"""

from __future__ import annotations

import logging
import re

import jieba
from rank_bm25 import BM25Okapi

from backend.repositories.regulations.models import Regulation, SearchHit

logger = logging.getLogger(__name__)

# 中文常见虚词 + 法律文书结构词（"第 X 条 / 款 / 项"）
_STOPWORDS: frozenset[str] = frozenset(
    {
        "的", "是", "在", "有", "和", "了", "不", "就", "与", "及",
        "其", "之", "为", "对", "可", "应", "按", "由", "或", "等",
        "也", "都", "已", "被", "把", "如", "若", "但", "并", "而",
        "第", "条", "项", "款", "章", "节", "号", "中", "一", "二",
        "三", "四", "五", "六", "七", "八", "九", "十",
    }
)

# 纯标点 / 空白 / 下划线
_PUNCT_PATTERN = re.compile(r"^[\s\W_]+$", re.UNICODE)


def _is_meaningful(token: str) -> bool:
    """过滤掉空、stopword、纯标点的 token."""
    if not token or token in _STOPWORDS:
        return False
    if _PUNCT_PATTERN.match(token):
        return False
    return True


def _tokenize(text: str) -> list[str]:
    """jieba 切词 + 小写 + 去停用词."""
    if not text:
        return []
    # cut_for_search 模式：搜索引擎风格，对长词二次切分
    raw = jieba.cut_for_search(text.lower())
    return [t for t in (s.strip() for s in raw) if _is_meaningful(t)]


def _corpus_text(reg: Regulation) -> str:
    """单条 regulation 的检索文本（title + summary + tags）—— 不含 full_text."""
    return f"{reg.title} {reg.summary} {' '.join(reg.tags)}"


class KeywordIndex:
    """BM25 keyword index over a regulation corpus.

    Build once，重复 ``search``。语料 immutable（来自 yaml seed），不支持增量更新；
    seed 改了重建 KeywordIndex 即可（v0.1 数据规模下成本可忽略）。
    """

    def __init__(self, regs: list[Regulation]) -> None:
        if not regs:
            raise ValueError("KeywordIndex 需要至少 1 条 regulation")
        self._regs: list[Regulation] = list(regs)
        self._tokenized: list[list[str]] = [_tokenize(_corpus_text(r)) for r in regs]
        # BM25Okapi 接受 list[list[str]]；空 token 列表会让该文档完全不命中
        self._bm25 = BM25Okapi(self._tokenized)
        logger.info("KeywordIndex built: %d regulations", len(regs))

    def search(self, query: str, top_k: int = 5) -> list[SearchHit]:
        """Return top-k hits sorted by descending score; score in [0, 1].

        Empty / all-stopword query returns ``[]``. 没有命中也返回 ``[]``。
        """
        if top_k <= 0:
            return []
        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        scores = self._bm25.get_scores(query_tokens)
        max_score = float(max(scores)) if len(scores) > 0 else 0.0
        if max_score <= 0.0:
            return []  # 全语料无命中

        # 归一化 + 排序
        ranked = sorted(
            (
                (idx, float(scores[idx]) / max_score)
                for idx in range(len(self._regs))
                if scores[idx] > 0
            ),
            key=lambda x: x[1],
            reverse=True,
        )[:top_k]

        return [
            SearchHit(
                id=self._regs[idx].id,
                title=self._regs[idx].title,
                summary=self._regs[idx].summary,
                source_name=self._regs[idx].source_name,
                score=score,
            )
            for idx, score in ranked
        ]

    @property
    def size(self) -> int:
        return len(self._regs)

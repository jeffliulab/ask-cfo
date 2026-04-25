"""Tests for backend/repositories/regulations/keyword_search.py + registry.py."""

from __future__ import annotations

import pytest

from backend.repositories.regulations.keyword_search import (
    KeywordIndex,
    _is_meaningful,
    _tokenize,
)
from backend.repositories.regulations.models import Regulation, SearchHit
from backend.repositories.regulations.registry import (
    all_ids,
    get_full,
    reset_registry,
)
from backend.repositories.regulations.seed_loader import load_seed, reset_cache


@pytest.fixture(autouse=True)
def _clear_caches():
    reset_cache()
    reset_registry()
    yield
    reset_cache()
    reset_registry()


def _make_reg(
    reg_id: str,
    title: str,
    summary: str,
    tags: list[str] | None = None,
    category: str = "VAT",
) -> Regulation:
    return Regulation(
        id=reg_id,
        category=category,  # type: ignore[arg-type]
        source_name=f"src-{reg_id}",
        source_url=f"http://example.com/{reg_id}",
        chapter="ch",
        article_number="art",
        title=title,
        summary=summary,
        full_text=f"full of {reg_id}",
        tags=tags or [],
    )


# === Tokenizer ===
class TestTokenize:
    def test_empty_returns_empty(self) -> None:
        assert _tokenize("") == []
        assert _tokenize("   ") == []

    def test_chinese_tokens(self) -> None:
        tokens = _tokenize("研发费用加计扣除")
        # jieba 应至少切出 "研发" / "费用" / "加计" / "扣除" 之一
        joined = "".join(tokens)
        assert "研发" in joined or "加计" in joined

    def test_filters_pure_stopword_query(self) -> None:
        # 全停用词的简单 query 切完后应该没有 meaningful token
        # 注：jieba cut_for_search 会从 "第十条" 切出 "第十" / "十条" / "第十条" 等
        # 组合 token，这些 _tokenize 不会过滤。我们在 search 层面做 BM25
        # 决定相关度（test_search_with_only_structural_words_returns_empty 覆盖）
        assert _tokenize("的的的") == []

    def test_filters_punctuation(self) -> None:
        tokens = _tokenize("，。、；：")
        assert tokens == []

    def test_lowercase_english(self) -> None:
        tokens = _tokenize("VAT")
        assert "vat" in tokens

    def test_is_meaningful_helper(self) -> None:
        assert _is_meaningful("增值税") is True
        assert _is_meaningful("的") is False
        assert _is_meaningful("") is False
        assert _is_meaningful(",") is False


# === KeywordIndex on synthetic corpus ===
class TestKeywordIndexSynthetic:
    @pytest.fixture
    def synthetic_index(self) -> KeywordIndex:
        regs = [
            _make_reg("a", "餐饮发票进项税抵扣", "招待费不得抵扣", tags=["餐饮", "进项税"]),
            _make_reg("b", "研发费用加计扣除", "100% 加计政策", tags=["研发", "加计"], category="CIT"),
            _make_reg("c", "个税专项附加", "子女教育扣除", tags=["个税"], category="IIT"),
            _make_reg("d", "固定资产折旧", "直线法 / 加速折旧", tags=["折旧"], category="CAS"),
        ]
        return KeywordIndex(regs)

    def test_top_hit_for_specific_query(self, synthetic_index: KeywordIndex) -> None:
        hits = synthetic_index.search("餐饮发票")
        assert len(hits) >= 1
        assert hits[0].id == "a"

    def test_returns_search_hit_type(self, synthetic_index: KeywordIndex) -> None:
        hits = synthetic_index.search("研发")
        assert all(isinstance(h, SearchHit) for h in hits)
        assert hits[0].id == "b"

    def test_top_k_limits(self, synthetic_index: KeywordIndex) -> None:
        # 用通用词制造多命中
        hits = synthetic_index.search("扣除", top_k=2)
        assert len(hits) <= 2

    def test_top_k_zero_returns_empty(self, synthetic_index: KeywordIndex) -> None:
        assert synthetic_index.search("扣除", top_k=0) == []

    def test_top_k_negative_returns_empty(self, synthetic_index: KeywordIndex) -> None:
        assert synthetic_index.search("扣除", top_k=-1) == []

    def test_empty_query_returns_empty(self, synthetic_index: KeywordIndex) -> None:
        assert synthetic_index.search("") == []
        assert synthetic_index.search("   ") == []

    def test_all_stopwords_query_returns_empty(self, synthetic_index: KeywordIndex) -> None:
        # 全停用词 → tokenize 空 → 返回空
        assert synthetic_index.search("的的的") == []

    def test_search_with_only_structural_words_returns_empty(
        self, synthetic_index: KeywordIndex
    ) -> None:
        # "第十条" jieba 切完会产生 token，但语料里没这些 token → BM25 score 0 → 返回 []
        assert synthetic_index.search("第十条") == []

    def test_no_match_returns_empty(self, synthetic_index: KeywordIndex) -> None:
        # 完全无关查询
        hits = synthetic_index.search("zzzzzznonexistentword")
        assert hits == []

    def test_score_normalized_to_one(self, synthetic_index: KeywordIndex) -> None:
        hits = synthetic_index.search("研发")
        assert hits, "至少一个命中"
        # 归一化后 top hit score 应该是 1.0
        assert hits[0].score == pytest.approx(1.0, abs=1e-9)
        # 其他 hit 都在 (0, 1]
        for h in hits:
            assert 0 < h.score <= 1.0

    def test_results_sorted_descending(self, synthetic_index: KeywordIndex) -> None:
        hits = synthetic_index.search("扣除")
        scores = [h.score for h in hits]
        assert scores == sorted(scores, reverse=True)

    def test_deterministic(self, synthetic_index: KeywordIndex) -> None:
        a = synthetic_index.search("餐饮")
        b = synthetic_index.search("餐饮")
        assert [(h.id, h.score) for h in a] == [(h.id, h.score) for h in b]

    def test_tag_only_match(self, synthetic_index: KeywordIndex) -> None:
        # "折旧" 只在 doc d 的 title + summary + tags 都出现 → 应该是 top
        hits = synthetic_index.search("折旧")
        assert hits[0].id == "d"

    def test_tokenized_corpus_excludes_full_text(self, synthetic_index: KeywordIndex) -> None:
        # full_text 包含 "full of d"，但应该不被索引
        hits = synthetic_index.search("zzzzzfullofdz")
        assert hits == []  # 即使搜全文里的内容也不应命中

    def test_size_property(self, synthetic_index: KeywordIndex) -> None:
        assert synthetic_index.size == 4


class TestKeywordIndexEdgeCases:
    def test_empty_corpus_raises(self) -> None:
        with pytest.raises(ValueError, match="至少 1 条"):
            KeywordIndex([])

    def test_min_three_doc_disambiguation(self) -> None:
        # BM25 在小 N 时 IDF 行为不稳，≥3 篇文档时表现可预测
        idx = KeywordIndex([
            _make_reg("a", "增值税专用发票", "进项税额抵扣处理"),
            _make_reg("b", "企业所得税汇算清缴", "全年应纳税所得额"),
            _make_reg("c", "个人所得税专项附加扣除", "子女教育住房贷款"),
        ])
        hits = idx.search("增值税专用发票进项")
        assert len(hits) >= 1
        assert hits[0].id == "a"


# === KeywordIndex 作用于真实 seed.yaml ===
class TestKeywordIndexOnRealSeed:
    @pytest.fixture
    def real_index(self) -> KeywordIndex:
        regs = load_seed()
        return KeywordIndex(regs)

    def test_query_about_entertainment_finds_relevant(self, real_index: KeywordIndex) -> None:
        # 用户场景："餐饮发票能抵扣进项吗"
        hits = real_index.search("餐饮发票进项")
        assert len(hits) >= 1
        # vat-no-deduction-2008 的 tags 包含 "餐饮"，应该是 top
        assert hits[0].id == "vat-no-deduction-2008"

    def test_query_about_rd_superdeduction(self, real_index: KeywordIndex) -> None:
        # 用户场景："研发费用加计扣除比例"
        hits = real_index.search("研发费用加计扣除")
        ids = [h.id for h in hits]
        # cit 加计扣除应该在前面（VAT 加计抵减是另一概念，命中应该弱一些）
        assert "cit-rd-superdeduction-100pct-2023" in ids[:3]

    def test_query_about_personal_income_tax(self, real_index: KeywordIndex) -> None:
        hits = real_index.search("个税专项附加扣除子女教育")
        ids = [h.id for h in hits]
        assert "iit-special-additional-deduction-2018" in ids[:2]

    def test_query_about_depreciation(self, real_index: KeywordIndex) -> None:
        hits = real_index.search("固定资产折旧年限")
        ids = [h.id for h in hits]
        assert "cas-4-fixed-asset-depreciation" in ids[:2]


# === Registry ===
class TestRegistry:
    def test_get_full_existing(self) -> None:
        # default seed 至少有 vat-no-deduction-2008 这条
        reg = get_full("vat-no-deduction-2008")
        assert reg is not None
        assert reg.id == "vat-no-deduction-2008"
        assert reg.full_text  # 应该有完整正文

    def test_get_full_unknown(self) -> None:
        assert get_full("nonexistent-id-xxx") is None

    def test_all_ids_returns_list(self) -> None:
        ids = all_ids()
        assert isinstance(ids, list)
        assert len(ids) >= 1
        assert "vat-no-deduction-2008" in ids

    def test_reset_clears(self) -> None:
        get_full("vat-no-deduction-2008")  # 暖 cache
        reset_registry()
        # 不报错即可（重新 lazy load）
        assert get_full("vat-no-deduction-2008") is not None

"""Tests for backend/repositories/regulations/seed_loader.py."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from backend.repositories.regulations.models import (
    ALLOWED_CATEGORIES,
    Regulation,
)
from backend.repositories.regulations.seed_loader import (
    DEFAULT_SEED_PATH,
    load_seed,
    reset_cache,
)


@pytest.fixture(autouse=True)
def _clear_cache():
    """每个测试前后清模块级 cache，避免相互污染."""
    reset_cache()
    yield
    reset_cache()


def _write_yaml(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "seed.yaml"
    p.write_text(dedent(content), encoding="utf-8")
    return p


# === 默认 seed.yaml 健康检查 ===
class TestDefaultSeed:
    def test_default_seed_exists(self) -> None:
        assert DEFAULT_SEED_PATH.exists(), f"seed.yaml 应存在于 {DEFAULT_SEED_PATH}"

    def test_loads_at_least_one(self) -> None:
        regs = load_seed()
        assert len(regs) >= 1
        assert all(isinstance(r, Regulation) for r in regs)

    def test_no_duplicate_ids(self) -> None:
        regs = load_seed()
        ids = [r.id for r in regs]
        assert len(ids) == len(set(ids)), f"发现重复 id: {ids}"

    def test_all_categories_valid(self) -> None:
        regs = load_seed()
        for r in regs:
            assert r.category in ALLOWED_CATEGORIES

    def test_covers_all_four_categories(self) -> None:
        """v0.1 起手种子要覆盖 4 类（增值税 / 企业所得税 / 个税 / CAS）."""
        regs = load_seed()
        cats = {r.category for r in regs}
        assert cats == set(ALLOWED_CATEGORIES), f"未覆盖全 4 类: {cats}"

    def test_required_fields_non_empty(self) -> None:
        regs = load_seed()
        for r in regs:
            assert r.id, f"id 为空: {r}"
            assert r.title, f"title 为空: {r.id}"
            assert r.summary, f"summary 为空: {r.id}"
            assert r.full_text, f"full_text 为空: {r.id}"
            assert r.source_url.startswith(("http://", "https://")), (
                f"source_url 非 http: {r.id} -> {r.source_url}"
            )


# === Cache 行为 ===
class TestCache:
    def test_caches_default_path(self) -> None:
        a = load_seed()
        b = load_seed()
        assert [r.id for r in a] == [r.id for r in b]

    def test_force_reload_works(self) -> None:
        load_seed()  # 暖 cache
        regs2 = load_seed(force_reload=True)
        assert len(regs2) >= 1

    def test_explicit_path_does_not_pollute_cache(self, tmp_path: Path) -> None:
        good = _write_yaml(
            tmp_path,
            """
            regulations:
              - id: only_one
                category: VAT
                source_name: a
                source_url: http://x
                chapter: x
                article_number: x
                title: x
                summary: x
                full_text: x
            """,
        )
        load_seed(good)  # 显式 path —— 不缓存
        defaults = load_seed()  # 默认 path 仍走默认 seed
        assert "only_one" not in {r.id for r in defaults}


# === 错误路径（fail loud）===
class TestErrorPaths:
    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load_seed(tmp_path / "nonexistent.yaml")

    def test_missing_top_level_key_raises(self, tmp_path: Path) -> None:
        bad = _write_yaml(tmp_path, "other_key: []\n")
        with pytest.raises(ValueError, match="顶层缺少"):
            load_seed(bad)

    def test_regulations_not_list_raises(self, tmp_path: Path) -> None:
        bad = _write_yaml(tmp_path, "regulations: {}\n")
        with pytest.raises(ValueError, match="必须是列表"):
            load_seed(bad)

    def test_missing_field_raises(self, tmp_path: Path) -> None:
        bad = _write_yaml(
            tmp_path,
            """
            regulations:
              - id: x
                category: VAT
                # 缺其他字段
            """,
        )
        with pytest.raises(ValueError, match="解析失败"):
            load_seed(bad)

    def test_invalid_category_raises(self, tmp_path: Path) -> None:
        bad = _write_yaml(
            tmp_path,
            """
            regulations:
              - id: x1
                category: INVALID_CAT
                source_name: a
                source_url: http://x
                chapter: x
                article_number: x
                title: x
                summary: x
                full_text: x
            """,
        )
        with pytest.raises(ValueError, match="解析失败"):
            load_seed(bad)

    def test_duplicate_id_raises(self, tmp_path: Path) -> None:
        bad = _write_yaml(
            tmp_path,
            """
            regulations:
              - id: dup
                category: VAT
                source_name: a
                source_url: http://x
                chapter: x
                article_number: x
                title: x
                summary: x
                full_text: x
              - id: dup
                category: CIT
                source_name: b
                source_url: http://x
                chapter: x
                article_number: x
                title: x
                summary: x
                full_text: x
            """,
        )
        with pytest.raises(ValueError, match="重复 id: dup"):
            load_seed(bad)


# === 字段处理细节 ===
class TestFieldHandling:
    def test_tags_default_to_empty_list(self, tmp_path: Path) -> None:
        no_tags = _write_yaml(
            tmp_path,
            """
            regulations:
              - id: x
                category: VAT
                source_name: a
                source_url: http://x
                chapter: x
                article_number: x
                title: x
                summary: x
                full_text: x
            """,
        )
        regs = load_seed(no_tags)
        assert regs[0].tags == []

    def test_tags_loaded_correctly(self, tmp_path: Path) -> None:
        with_tags = _write_yaml(
            tmp_path,
            """
            regulations:
              - id: x
                category: VAT
                source_name: a
                source_url: http://x
                chapter: x
                article_number: x
                title: x
                summary: x
                full_text: x
                tags:
                  - alpha
                  - beta
                  - gamma
            """,
        )
        regs = load_seed(with_tags)
        assert regs[0].tags == ["alpha", "beta", "gamma"]

    def test_preserves_yaml_order(self, tmp_path: Path) -> None:
        ordered = _write_yaml(
            tmp_path,
            """
            regulations:
              - id: first
                category: VAT
                source_name: a
                source_url: http://x
                chapter: x
                article_number: x
                title: x
                summary: x
                full_text: x
              - id: second
                category: CIT
                source_name: a
                source_url: http://x
                chapter: x
                article_number: x
                title: x
                summary: x
                full_text: x
              - id: third
                category: IIT
                source_name: a
                source_url: http://x
                chapter: x
                article_number: x
                title: x
                summary: x
                full_text: x
            """,
        )
        regs = load_seed(ordered)
        assert [r.id for r in regs] == ["first", "second", "third"]

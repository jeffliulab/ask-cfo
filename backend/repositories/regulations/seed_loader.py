"""法规种子库加载器 —— Day 1 of v0.1.0.

`load_seed(path)` 从 yaml 加载 list[Regulation]；模块级 lazy cache 避免重复 IO。
重复 id / 缺字段 / 非法 category 都报错（fail loud）。

测试可用 ``reset_cache()`` 清缓存；用显式 ``path`` 加载时不污染默认缓存。
"""

from __future__ import annotations

import logging
from pathlib import Path

import yaml

from backend.repositories.regulations.models import (
    ALLOWED_CATEGORIES,
    Regulation,
)

logger = logging.getLogger(__name__)

# /Users/.../ask-cfo/backend/repositories/regulations/seed_loader.py
#   parents[0] = regulations/
#   parents[1] = repositories/
#   parents[2] = backend/
DEFAULT_SEED_PATH: Path = (
    Path(__file__).parents[2] / "data" / "regulations" / "seed.yaml"
)

_REQUIRED_FIELDS = {
    "id",
    "category",
    "source_name",
    "source_url",
    "chapter",
    "article_number",
    "title",
    "summary",
    "full_text",
}

_REGULATIONS_CACHE: dict[str, Regulation] | None = None


def load_seed(
    path: Path | None = None, *, force_reload: bool = False
) -> list[Regulation]:
    """Load regulations from yaml.

    Args:
        path: 显式 yaml 路径；None 则用 ``DEFAULT_SEED_PATH``，且结果会被缓存
        force_reload: 强制重读（仅对默认路径生效）

    Returns:
        list[Regulation]，按 yaml 出现顺序

    Raises:
        FileNotFoundError: yaml 不存在
        ValueError: 顶层结构错 / 重复 id / 缺字段 / 非法 category
    """
    global _REGULATIONS_CACHE

    use_default = path is None
    if use_default and _REGULATIONS_CACHE is not None and not force_reload:
        return list(_REGULATIONS_CACHE.values())

    seed_path = path or DEFAULT_SEED_PATH
    if not seed_path.exists():
        raise FileNotFoundError(f"seed yaml 不存在: {seed_path}")

    with seed_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict) or "regulations" not in data:
        raise ValueError(f"seed yaml 顶层缺少 'regulations' 键: {seed_path}")

    raw_entries = data["regulations"]
    if not isinstance(raw_entries, list):
        raise ValueError(
            f"'regulations' 必须是列表，实际类型: {type(raw_entries).__name__}"
        )

    regs: dict[str, Regulation] = {}
    for idx, entry in enumerate(raw_entries):
        try:
            reg = _entry_to_regulation(entry)
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"seed entry #{idx} 解析失败: {exc}") from exc
        if reg.id in regs:
            raise ValueError(f"seed 重复 id: {reg.id}")
        regs[reg.id] = reg

    if use_default:
        _REGULATIONS_CACHE = regs

    logger.info("loaded %d regulations from %s", len(regs), seed_path)
    return list(regs.values())


def _entry_to_regulation(entry: object) -> Regulation:
    """yaml 单项 → Regulation；缺字段 / 类型错 raise."""
    if not isinstance(entry, dict):
        raise TypeError(f"entry 必须是 dict，实际: {type(entry).__name__}")

    missing = _REQUIRED_FIELDS - set(entry.keys())
    if missing:
        raise KeyError(f"缺字段: {sorted(missing)}")

    category = entry["category"]
    if category not in ALLOWED_CATEGORIES:
        raise ValueError(
            f"非法 category: {category!r}（合法：{ALLOWED_CATEGORIES}）"
        )

    return Regulation(
        id=str(entry["id"]),
        category=category,
        source_name=str(entry["source_name"]),
        source_url=str(entry["source_url"]),
        chapter=str(entry["chapter"]),
        article_number=str(entry["article_number"]),
        title=str(entry["title"]),
        summary=str(entry["summary"]),
        full_text=str(entry["full_text"]),
        tags=[str(t) for t in entry.get("tags", [])],
    )


def reset_cache() -> None:
    """Clear module-level cache —— 测试用."""
    global _REGULATIONS_CACHE
    _REGULATIONS_CACHE = None

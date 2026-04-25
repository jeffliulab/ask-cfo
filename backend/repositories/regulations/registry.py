"""Regulation registry —— Day 2 of v0.1.0.

简单 id → Regulation 字典，lazy-load 默认 seed。
agent 通过 ``get_full(id)`` 在 ``get_regulation`` tool 里取全文。
"""

from __future__ import annotations

from backend.repositories.regulations.models import Regulation
from backend.repositories.regulations.seed_loader import load_seed

_REGISTRY: dict[str, Regulation] | None = None


def get_full(reg_id: str) -> Regulation | None:
    """Lookup full Regulation by id；lazy-load 默认 seed。

    Returns:
        匹配的 Regulation；id 不存在返回 None
    """
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = {r.id: r for r in load_seed()}
    return _REGISTRY.get(reg_id)


def all_ids() -> list[str]:
    """所有已加载 regulation 的 id（调试用）."""
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = {r.id: r for r in load_seed()}
    return list(_REGISTRY.keys())


def reset_registry() -> None:
    """Clear lazy cache —— 测试用."""
    global _REGISTRY
    _REGISTRY = None


def set_registry(regs: list[Regulation]) -> None:
    """Inject regs into module-level cache —— 测试用，避免 registry 与 KeywordIndex
    数据源不一致（agent dispatch ``get_regulation`` 走 registry，搜索走 index）.
    """
    global _REGISTRY
    _REGISTRY = {r.id: r for r in regs}

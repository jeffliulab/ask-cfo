"""Pydantic response schemas —— routes 层独有.

按 stacks/python-backend.md：request / response schema 使用 Pydantic.

v0.1 仅含 chat 与 healthz 的契约；CFO 模块的 schema（凭证草稿响应 /
报表响应 / 法规检索响应等）随各模块上线时增补.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class CitationOut(BaseModel):
    """与 backend.interfaces.Citation 形状一致的 wire 模型."""

    label: str
    source_name: str
    url: str


class HealthResponse(BaseModel):
    """``GET /healthz`` 的响应体."""

    status: Literal["ok", "degraded"]
    version: str

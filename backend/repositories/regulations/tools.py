"""LLM tool schemas + dispatcher —— Day 3 of v0.1.0.

为 RegulationAgent 暴露两个工具：
  - ``search_regulations(query, top_k=5)`` → 返回 SearchHit list
  - ``get_regulation(id)`` → 返回完整 Regulation 字段（含 source_url、full_text）

双格式 schema：``anthropic_schema()`` 和 ``openai_schema()`` 输出同一组工具的不同
JSON wrapper（Anthropic 用 ``input_schema``，OpenAI 用 ``parameters``），runtime
按 provider 选用，避免后续切 provider 重写。

``dispatch(name, args)`` 把 LLM 给出的 tool_use call 路由到真实 backend：
返回 plain dict（非 dataclass）便于 JSON 序列化进 LLM messages。
"""

from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Any

from backend.repositories.regulations.keyword_search import KeywordIndex
from backend.repositories.regulations.registry import get_full

logger = logging.getLogger(__name__)


# === Tool 名称 + JSON Schema ===
SEARCH_TOOL_NAME = "search_regulations"
GET_TOOL_NAME = "get_regulation"

_SEARCH_DESCRIPTION = (
    "在中国财税法规库中按关键词检索条款。返回 top-k 条款的 id / 标题 / 摘要 / 出处 / 相关度分数。"
    "用于初步定位；具体条款全文需要再调 get_regulation(id) 取。"
)

_SEARCH_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "中文自然语言查询，如 '研发费用加计扣除' / '餐饮发票能抵进项吗'",
        },
        "top_k": {
            "type": "integer",
            "description": "返回前 K 条结果，默认 5，建议 3-8",
            "default": 5,
            "minimum": 1,
            "maximum": 20,
        },
    },
    "required": ["query"],
}

_GET_DESCRIPTION = (
    "按 id 取一条法规的完整内容（含正文、章节、source_url）。id 必须从 search_regulations "
    "返回结果里来；不要凭空构造 id。返回 None 表示 id 不存在。"
)

_GET_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "id": {
            "type": "string",
            "description": "条款 id，如 'cit-rd-superdeduction-100pct-2023'",
        },
    },
    "required": ["id"],
}


def anthropic_schema() -> list[dict[str, Any]]:
    """Anthropic ``messages.stream(tools=[...])`` 格式（直接喂给 SDK）."""
    return [
        {
            "name": SEARCH_TOOL_NAME,
            "description": _SEARCH_DESCRIPTION,
            "input_schema": _SEARCH_INPUT_SCHEMA,
        },
        {
            "name": GET_TOOL_NAME,
            "description": _GET_DESCRIPTION,
            "input_schema": _GET_INPUT_SCHEMA,
        },
    ]


def openai_schema() -> list[dict[str, Any]]:
    """OpenAI / DeepSeek ``chat.completions.create(tools=[...])`` 格式."""
    return [
        {
            "type": "function",
            "function": {
                "name": SEARCH_TOOL_NAME,
                "description": _SEARCH_DESCRIPTION,
                "parameters": _SEARCH_INPUT_SCHEMA,
            },
        },
        {
            "type": "function",
            "function": {
                "name": GET_TOOL_NAME,
                "description": _GET_DESCRIPTION,
                "parameters": _GET_INPUT_SCHEMA,
            },
        },
    ]


# === Dispatcher（执行真实后端） ===
def dispatch(name: str, args: dict[str, Any], index: KeywordIndex) -> dict[str, Any]:
    """Execute one tool call.

    Args:
        name: tool name 来自 LLM 的 tool_use block
        args: 已解析的 JSON args
        index: 当前生效的 KeywordIndex

    Returns:
        dict：tool result，会被 JSON 序列化喂回 LLM。
        - search_regulations → {"hits": [...]}（每个 hit 是 SearchHit 的 dict）
        - get_regulation → {"regulation": ...} 或 {"regulation": None, "error": "..."}

    Raises:
        ValueError: 未知 tool name / 参数错
    """
    logger.info("[regulation-tools] dispatch %s args=%s", name, args)

    if name == SEARCH_TOOL_NAME:
        query = args.get("query", "")
        top_k = int(args.get("top_k", 5))
        if not isinstance(query, str):
            raise ValueError(f"query 必须是 str，实际: {type(query).__name__}")
        hits = index.search(query, top_k=top_k)
        return {"hits": [asdict(h) for h in hits]}

    if name == GET_TOOL_NAME:
        reg_id = args.get("id", "")
        if not isinstance(reg_id, str) or not reg_id:
            raise ValueError("id 必须是非空字符串")
        reg = get_full(reg_id)
        if reg is None:
            return {
                "regulation": None,
                "error": f"id '{reg_id}' 不存在；请先用 search_regulations 找到正确 id",
            }
        return {"regulation": asdict(reg)}

    raise ValueError(
        f"未知 tool: {name}（可用：{SEARCH_TOOL_NAME} / {GET_TOOL_NAME}）"
    )

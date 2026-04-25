"""Magic numbers, endpoints, defaults —— 集中放这里，避免散落到业务代码.

按 agent-rules/principles/engineering.md：魔法数字提取到 constants.py。

v0.1 各 CFO 模块（凭证 / 报税 / 法规问答）的具体常量等模块实现时再加。
"""

from __future__ import annotations

# === HTTP 通用 ===
DEFAULT_HTTP_TIMEOUT_SEC = 30
DEFAULT_HTTP_RETRIES = 1

# === Chat / LLM ===
DEFAULT_CHAT_MAX_TOKENS = 2048

# === CFO 模块占位（实现时填充） ===
# DEFAULT_VOUCHER_PER_PAGE = 20
# DEFAULT_REGULATION_SEARCH_LIMIT = 10
# 国税总局公告 base URL、巨潮 cninfo、会计准则数据库等接口配置

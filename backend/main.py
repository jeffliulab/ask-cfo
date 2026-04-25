"""FastAPI application entry —— uvicorn backend.main:app --reload --port 8000.

按 stacks/python-backend.md：
- routes/ 注册到 main 这里；不在 main 写业务
- CORS 显式白名单（不通配 *），来源于 config.api.cors_origins
- 启动 / 关闭挂在 lifespan，不用过时的 on_event 钩子

v0.1 路由：仅 /healthz 和 /api/v1/chat/stream（共享自 fin-pilot）；CFO 模块路由
（凭证 / 月结 / 报表 / 报税 / 法规问答）随各 service 上线时注册.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend import __version__
from backend.config import get_settings
from backend.routes import chat, health

logger = logging.getLogger(__name__)


def _setup_logging(level: str) -> None:
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    _setup_logging(settings.log_level)
    logger.info(
        "agent-as-a-cfo backend v%s 启动 (LLM=%s)",
        __version__,
        settings.llm.provider.value,
    )
    yield
    logger.info("agent-as-a-cfo backend v%s 关闭", __version__)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="agent-as-a-cfo",
        version=__version__,
        description="财务记账与报税 Agent —— 三栏 AI 工作台",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    # 注册 routes
    app.include_router(health.router)
    app.include_router(chat.router)
    # v0.1+ 加 CFO 模块 routes：bookkeeping / month_end / reports / tax_filing / regulations

    return app


app = create_app()

"""FastAPI 应用入口：注册中间件、异常处理、路由。"""

import logging
import time

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.exceptions import (
    AppException,
    app_exception_handler,
    unhandled_exception_handler,
)
from app.routers import chat, feedback, ops, orders, trace, users

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("mewhelp")

app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """请求日志中间件：记录方法 / 路径 / 状态码 / 耗时。"""
    start = time.perf_counter()
    response = await call_next(request)
    cost_ms = (time.perf_counter() - start) * 1000
    logger.info("%s %s -> %d (%.1fms)", request.method, request.url.path,
                response.status_code, cost_ms)
    return response


# 统一异常处理：业务异常 -> 对应状态码；未知异常 -> 500
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

# 注册路由
app.include_router(users.router)
app.include_router(orders.router)
app.include_router(chat.router)
app.include_router(trace.router)
app.include_router(feedback.router)
app.include_router(ops.router)

# 静态页面（极简聊天页，用于直观验证 SSE）
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/health", tags=["system"])
def health() -> dict:
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}

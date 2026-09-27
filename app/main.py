"""FastAPI 应用入口：目前仅健康检查，后续 P1 起挂载 chat / kb / orders 等路由。"""

import logging

from fastapi import FastAPI

from app.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("mewhelp")

app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)


@app.get("/health", tags=["system"])
def health() -> dict:
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}

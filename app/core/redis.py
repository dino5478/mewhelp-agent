"""Redis 客户端：全局单例，带容错。后续用于缓存与会话状态存储。"""

import logging

import redis

from app.core.config import settings

logger = logging.getLogger("mewhelp")

_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    """获取 Redis 客户端（懒加载，进程内复用同一个连接池）。"""
    global _client
    if _client is None:
        _client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _client


def ping_redis() -> bool:
    """健康检查用：Redis 不可用时返回 False，而不是抛异常。"""
    try:
        return bool(get_redis().ping())
    except Exception as exc:  # noqa: BLE001
        logger.warning("redis ping failed: %s", exc)
        return False

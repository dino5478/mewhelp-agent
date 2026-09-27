"""图状态的检查点存储：放 Redis，进程重启也不丢中断现场。

注意要用 AsyncRedisSaver：同步版没实现 aget_tuple，异步图跑不动。
"""

import redis.asyncio as aioredis
from langgraph.checkpoint.redis.aio import AsyncRedisSaver

from app.core.config import settings

_saver: AsyncRedisSaver | None = None


async def get_checkpointer() -> AsyncRedisSaver:
    global _saver
    if _saver is None:
        client = aioredis.from_url(settings.REDIS_URL)
        _saver = AsyncRedisSaver(redis_client=client)
        await _saver.asetup()
    return _saver

import functools
import json
from collections.abc import Callable
from typing import Any

from fastapi.encoders import jsonable_encoder
from redis.asyncio import Redis

from app.core.config import settings


class RedisService:
    def __init__(self):
        self.redis = Redis.from_url(settings.CELERY_RESULT_BACKEND, decode_responses=True)

    async def set_cache(self, key: str, data: dict | list, expire: int = 300):
        await self.redis.set(key, json.dumps(data), ex=expire)

    #
    async def get_cache(self, key: str) -> dict | list | None:
        data = await self.redis.get(key)
        if data:
            return json.loads(data)
        return None

    async def delete(self, key: str):
        """Delete one key"""
        await self.redis.delete(key)

    async def delete_pattern(self, pattern: str):
        """
        Delete all keys by mask (example 'batches_list:*').
        """
        keys = await self.redis.keys(pattern)
        if keys:
            await self.redis.delete(*keys)

    async def close(self):
        await self.redis.aclose()


redis_service = RedisService()


def cached(ttl: int, key_prefix: str):
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            safe_kwargs = {k: v for k, v in kwargs.items() if k != "session"}

            cache_key = key_prefix
            if safe_kwargs:
                sorted_items = sorted(safe_kwargs.items())
                args_str = ":".join(f"{k}_{v}" for k, v in sorted_items)
                cache_key = f"{key_prefix}:{args_str}"

            cached_data = await redis_service.get_cache(cache_key)
            if cached_data:
                return cached_data

            result = await func(*args, **kwargs)

            data_to_cache = jsonable_encoder(result)

            await redis_service.set_cache(cache_key, data_to_cache, expire=ttl)

            return result

        return wrapper

    return decorator

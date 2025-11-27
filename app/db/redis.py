import redis.asyncio as redis
from app.config import get_settings

settings = get_settings()

# Redis client singleton
_redis_client: redis.Redis | None = None


async def init_redis() -> redis.Redis:
    """Initialize Redis connection."""
    global _redis_client
    _redis_client = await redis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
    )
    return _redis_client


async def get_redis() -> redis.Redis:
    """Get Redis client instance."""
    global _redis_client
    if _redis_client is None:
        _redis_client = await init_redis()
    return _redis_client


async def close_redis():
    """Close Redis connection."""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None

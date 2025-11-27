"""
Cache service using Redis for query results.
Provides deterministic responses for identical inputs.
"""
import json
import hashlib
from typing import Optional, Dict, Any

from app.db.redis import get_redis
from app.config import get_settings

settings = get_settings()


class CacheService:
    """Service for caching query results in Redis."""

    def __init__(self):
        self.ttl = settings.cache_ttl_seconds
        self.prefix = "query"

    def _generate_cache_key(
        self,
        tenant_id: str,
        content_hash: str,
        cache_key_suffix: str = "",
    ) -> str:
        """
        Generate a unique cache key for a query request.

        Args:
            tenant_id: The tenant's ID
            content_hash: Hash of the query content
            cache_key_suffix: Optional suffix (e.g., assistant_id)

        Returns:
            A unique cache key string
        """
        return f"{self.prefix}:{tenant_id}:{content_hash}{cache_key_suffix}"

    async def get_cached_result(
        self,
        tenant_id: str,
        content_hash: str,
        cache_key_suffix: str = "",
    ) -> Optional[Dict[str, Any]]:
        """
        Get a cached query result if it exists.

        Args:
            tenant_id: The tenant's ID
            content_hash: Hash of the query content
            cache_key_suffix: Optional suffix (e.g., assistant_id)

        Returns:
            Cached result or None
        """
        redis = await get_redis()
        cache_key = self._generate_cache_key(tenant_id, content_hash, cache_key_suffix)

        cached = await redis.get(cache_key)
        if cached:
            return json.loads(cached)
        return None

    async def cache_result(
        self,
        tenant_id: str,
        content_hash: str,
        result: Dict[str, Any],
        cache_key_suffix: str = "",
    ) -> bool:
        """
        Cache a query result.

        Args:
            tenant_id: The tenant's ID
            content_hash: Hash of the query content
            result: The result to cache
            cache_key_suffix: Optional suffix (e.g., assistant_id)

        Returns:
            True if cached successfully
        """
        redis = await get_redis()
        cache_key = self._generate_cache_key(tenant_id, content_hash, cache_key_suffix)

        await redis.setex(
            cache_key,
            self.ttl,
            json.dumps(result, ensure_ascii=False),
        )
        return True

    async def invalidate_tenant_cache(self, tenant_id: str) -> int:
        """
        Invalidate all cached queries for a tenant.
        Useful when prompts or knowledge base are updated.

        Args:
            tenant_id: The tenant's ID

        Returns:
            Number of keys deleted
        """
        redis = await get_redis()
        pattern = f"{self.prefix}:{tenant_id}:*"

        # Use SCAN to find and delete keys (safer than KEYS for large datasets)
        deleted = 0
        cursor = 0
        while True:
            cursor, keys = await redis.scan(cursor, match=pattern, count=100)
            if keys:
                await redis.delete(*keys)
                deleted += len(keys)
            if cursor == 0:
                break

        return deleted

    async def get_cache_stats(self, tenant_id: str) -> Dict[str, Any]:
        """
        Get cache statistics for a tenant.

        Args:
            tenant_id: The tenant's ID

        Returns:
            Dict with cache statistics
        """
        redis = await get_redis()
        pattern = f"{self.prefix}:{tenant_id}:*"

        # Count keys
        count = 0
        cursor = 0
        while True:
            cursor, keys = await redis.scan(cursor, match=pattern, count=100)
            count += len(keys)
            if cursor == 0:
                break

        return {
            "tenant_id": tenant_id,
            "cached_evaluations": count,
            "ttl_seconds": self.ttl,
        }


# Singleton instance
_cache_service: CacheService | None = None


def get_cache_service() -> CacheService:
    """Get the singleton cache service instance."""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service

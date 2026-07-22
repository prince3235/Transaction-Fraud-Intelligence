"""
Enterprise Async Redis Velocity Store Client.

Provides real-time, sliding-window velocity aggregations (e.g. transaction count
and sum amount per account over a 10-minute window).

Fail-safe Guarantee:
All operations gracefully catch Redis errors, connection timeouts, or missing
Redis instances, returning neutral default metrics (count=0, sum=0.0) so that
ML inference pipelines never fail when Redis is unavailable.
"""
from __future__ import annotations

import logging
import os
import time
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

_redis_installed = False
try:
    import redis
    import redis.asyncio as aioredis
    _redis_installed = True
except ImportError:  # pragma: no cover
    aioredis = None
    logger.warning("redis package not installed — velocity store running in fallback mode.")


class AsyncRedisVelocityStore:
    """
    Async Redis velocity feature aggregator with automatic connection pooling
    and fail-safe fallback logic.
    """

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or REDIS_URL
        self._client: Optional[Any] = None
        self._is_disabled = False

    async def get_client(self) -> Optional[Any]:
        """Lazy-initialize async Redis client."""
        if self._is_disabled or not _redis_installed:
            return None
        if self._client is None:
            try:
                self._client = aioredis.from_url(
                    self.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=1.0,
                    socket_timeout=1.0,
                )
            except Exception as exc:
                logger.warning("Redis connection initialization failed: %s", exc)
                self._is_disabled = True
                return None
        return self._client

    async def record_transaction(
        self,
        account_id: str,
        amount: float,
        window_seconds: int = 600,
    ) -> bool:
        """
        Record a transaction event for an account in Redis sorted sets.
        Returns True on success, False on fallback.
        """
        client = await self.get_client()
        if client is None:
            return False

        try:
            now = time.time()
            member = f"{now}:{amount}"
            key = f"velocity:{account_id}"
            
            async with client.pipeline(transaction=True) as pipe:
                pipe.zadd(key, {member: now})
                # Evict entries older than window_seconds
                pipe.zremrangebyscore(key, 0, now - window_seconds)
                pipe.expire(key, window_seconds * 2)
                await pipe.execute()
            return True
        except Exception as exc:
            logger.debug("Redis record_transaction failed (non-fatal fallback): %s", exc)
            return False

    async def get_account_velocity(
        self,
        account_id: str,
        window_seconds: int = 600,
    ) -> Dict[str, float]:
        """
        Retrieve 10-minute velocity count and sum for an account.
        Returns neutral zero metrics if Redis is offline or unreachable.
        """
        fallback_metrics = {
            "velocity_count_10m": 0.0,
            "velocity_sum_10m": 0.0,
            "is_redis_active": 0.0,
        }

        client = await self.get_client()
        if client is None:
            return fallback_metrics

        try:
            now = time.time()
            key = f"velocity:{account_id}"
            min_score = now - window_seconds
            
            # Remove expired and fetch active elements in range
            async with client.pipeline(transaction=True) as pipe:
                pipe.zremrangebyscore(key, 0, min_score)
                pipe.zrangebyscore(key, min_score, "+inf")
                results = await pipe.execute()

            active_members = results[1] if len(results) > 1 else []
            count = float(len(active_members))
            
            total_sum = 0.0
            for item in active_members:
                try:
                    if ":" in str(item):
                        _, amt_str = str(item).split(":", 1)
                        total_sum += float(amt_str)
                except (ValueError, TypeError):
                    pass

            return {
                "velocity_count_10m": count,
                "velocity_sum_10m": total_sum,
                "is_redis_active": 1.0,
            }
        except Exception as exc:
            logger.debug("Redis get_account_velocity failed (non-fatal fallback): %s", exc)
            return fallback_metrics

    async def close(self) -> None:
        """Close Redis connection pool gracefully."""
        if self._client:
            try:
                await self._client.aclose()
            except Exception:
                pass
            self._client = None


velocity_store = AsyncRedisVelocityStore()

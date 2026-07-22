import pytest
from src.redis_client import AsyncRedisVelocityStore

@pytest.mark.asyncio
async def test_redis_fallback_when_offline():
    """Verify AsyncRedisVelocityStore fails safe returning zeros when Redis is offline."""
    store = AsyncRedisVelocityStore(redis_url="redis://invalid_host_123:6379/0")
    
    # Test record_transaction returns False safely without error
    recorded = await store.record_transaction("acc_123", 500.0)
    assert recorded is False
    
    # Test get_account_velocity returns zero metrics safely
    metrics = await store.get_account_velocity("acc_123")
    assert metrics["velocity_count_10m"] == 0.0
    assert metrics["velocity_sum_10m"] == 0.0
    assert metrics["is_redis_active"] == 0.0
    
    await store.close()

"""
Enterprise Real-Time Fraud Stream Simulator.

Provides:
- WebSocket-like continuous data generation
- Bursty fraud injection for demoing platform responsiveness
"""
import asyncio
import json
import random
import time
from datetime import datetime, timezone
from typing import AsyncGenerator, Dict, Any

from app.simulator import build_transaction


async def generate_transaction_stream(
    burst_fraud: bool = False,
    delay_ms: int = 500
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Simulates a continuous stream of financial transactions.
    If burst_fraud is True, occasionally injects clusters of fraudulent transactions.
    """
    fraud_burst_active = False
    burst_count = 0
    
    while True:
        # Determine if this transaction should be forced fraud
        is_fraud = False
        
        if burst_fraud:
            if fraud_burst_active:
                is_fraud = True
                burst_count -= 1
                if burst_count <= 0:
                    fraud_burst_active = False
            else:
                # 5% chance to start a fraud burst
                if random.random() < 0.05:
                    fraud_burst_active = True
                    burst_count = random.randint(3, 8)
                    
        if not is_fraud:
            # Base 2% chance of normal fraud
            is_fraud = random.random() < 0.02
            
        # Build transaction
        tx = build_transaction(fraud_forced=is_fraud)
        
        # Add timestamp
        tx["timestamp"] = datetime.now(timezone.utc).isoformat()
        tx["is_fraud_injected"] = is_fraud
        
        yield tx
        
        # Async delay to simulate network/processing
        await asyncio.sleep(delay_ms / 1000.0)

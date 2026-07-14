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

from app.simulator import build_transaction, _MERCHANT_RISK, _COUNTRY_RISK


def _random_tx_inputs(is_fraud: bool) -> dict:
    """Pick random simulator inputs biased by whether the tx should be fraud."""
    if is_fraud:
        merchant = random.choice(["Crypto Exchange", "Gambling", "Wire Transfer", "ATM Withdrawal"])
        country = random.choice(["Nigeria", "Russia", "Anonymous VPN", "UAE"])
        amount = random.uniform(5_000, 95_000)
        hour = random.choice([0, 1, 2, 22, 23])
        signals = random.randint(2, 5)
        new_dev = random.random() > 0.3
        velocity = random.random() > 0.4
    else:
        merchant = random.choice(["POS Retail", "Utility Bill", "E-Commerce", "Travel Agency"])
        country = random.choice(["India", "USA", "UK", "Germany"])
        amount = random.uniform(100, 8_000)
        hour = random.randint(8, 20)
        signals = random.randint(0, 1)
        new_dev = False
        velocity = False
    return {
        "amount": amount,
        "merchant_type": merchant,
        "country": country,
        "hour": hour,
        "suspicious_signals": signals,
        "is_new_device": new_dev,
        "velocity_flag": velocity,
    }


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
    sim_id = 9000

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

        # Build transaction with the correct (8-arg) signature.
        inputs = _random_tx_inputs(is_fraud)
        tx = build_transaction(
            amount=inputs["amount"],
            merchant_type=inputs["merchant_type"],
            country=inputs["country"],
            hour=inputs["hour"],
            suspicious_signals=inputs["suspicious_signals"],
            is_new_device=inputs["is_new_device"],
            velocity_flag=inputs["velocity_flag"],
            sim_id=sim_id,
        )
        sim_id += 1

        # Add timestamp + fraud flag for downstream consumers
        tx["timestamp"] = datetime.now(timezone.utc).isoformat()
        tx["is_fraud_injected"] = is_fraud

        yield tx

        # Async delay to simulate network/processing
        await asyncio.sleep(delay_ms / 1000.0)

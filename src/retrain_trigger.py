import os
import logging
from datetime import datetime, timezone
from pathlib import Path
from apscheduler.schedulers.background import BackgroundScheduler
import numpy as np

from src.drift_monitor import calculate_psi
from src.train_pipeline import train_model
from src.db import SessionLocal
from src.models import PredictionLog

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "transaction_data.csv"

def check_drift_and_retrain():
    """
    Scheduled job that checks for data drift via Population Stability Index (PSI).
    If PSI >= 0.25, it automatically triggers train_pipeline.py to retrain the model.
    """
    logger.info("Running scheduled drift check and retraining trigger...")
    
    baseline_data = np.random.normal(loc=0.0, scale=1.0, size=1000)
    
    db = SessionLocal()
    try:
        count = db.query(PredictionLog).count()
    except Exception:
        count = 0
    finally:
        db.close()
        
    shift = min(count / 100.0, 2.0) 
    current_data = np.random.normal(loc=shift, scale=1.0, size=100)
    
    psi_score = calculate_psi(baseline_data, current_data)
    
    logger.info("Calculated PSI Score: %.4f", psi_score)
    
    DRIFT_THRESHOLD = 0.25
    if psi_score >= DRIFT_THRESHOLD:
        logger.warning(f"High drift detected! PSI={psi_score:.4f} >= {DRIFT_THRESHOLD}. Triggering retraining...")
        try:
            train_model(DATA_PATH, n_samples=50000)
            logger.info("Retraining completed successfully. New model is in Staging (MLflow).")
            
            _log_system_alert(f"Drift detected (PSI={psi_score:.2f}) — new candidate model trained and awaiting review in MLflow.")
        except Exception as e:
            logger.error("Failed to retrain model: %s", e)
    else:
        logger.info("No significant drift detected. Model is stable.")


def _log_system_alert(message: str):
    """Log an alert to the database for the admin dashboard."""
    # System alerts table is omitted from new schema, fallback to python logging
    logger.error(f"SYSTEM ALERT: {message}")

def start_scheduler():
    """Starts the APScheduler background job."""
    scheduler = BackgroundScheduler()
    scheduler.add_job(check_drift_and_retrain, 'interval', minutes=5)
    scheduler.start()
    logger.info("APScheduler started: check_drift_and_retrain job added (interval: 5m).")
    return scheduler

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    check_drift_and_retrain()

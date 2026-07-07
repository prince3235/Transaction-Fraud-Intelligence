"""
Enterprise Model Registry.

Provides:
- Version tracking for trained models
- Metadata and metrics serialization
- Model promotion (active/production flag)
- Archiving and rollback support
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.db import SessionLocal
from src.models import ModelRegistry


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def list_model_versions(db_path: Path, include_archived: bool = False) -> List[Dict[str, Any]]:
    """Return all model versions in descending order of creation."""
    db = SessionLocal()
    try:
        query = db.query(ModelRegistry)
        if not include_archived:
            query = query.filter(ModelRegistry.is_archived == False)
        
        rows = query.order_by(ModelRegistry.id.desc()).all()
        return [{
            "id": r.id,
            "version": r.version,
            "pkl_path": r.pkl_path,
            "roc_auc": r.roc_auc,
            "pr_auc": r.pr_auc,
            "precision_val": r.precision_val,
            "recall_val": r.recall_val,
            "f1_val": r.f1_val,
            "n_estimators": r.n_estimators,
            "training_date": r.training_date,
            "dataset_size": r.dataset_size,
            "feature_count": r.feature_count,
            "notes": r.notes,
            "is_production": r.is_production,
            "is_archived": r.is_archived,
            "created_at": r.created_at
        } for r in rows]
    finally:
        db.close()


def get_active_model(db_path: Path) -> Optional[Dict[str, Any]]:
    """Return the currently active production model."""
    db = SessionLocal()
    try:
        row = db.query(ModelRegistry).filter(ModelRegistry.is_production == True).first()
        if row:
            return {
                "id": row.id,
                "version": row.version,
                "pkl_path": row.pkl_path,
                "roc_auc": row.roc_auc,
                "pr_auc": row.pr_auc,
                "precision_val": row.precision_val,
                "recall_val": row.recall_val,
                "f1_val": row.f1_val,
                "n_estimators": row.n_estimators,
                "training_date": row.training_date,
                "dataset_size": row.dataset_size,
                "feature_count": row.feature_count,
                "notes": row.notes,
                "is_production": row.is_production,
                "is_archived": row.is_archived,
                "created_at": row.created_at
            }
        return None
    finally:
        db.close()


def register_model(
    db_path: Path,
    pkl_path: str,
    roc_auc: float,
    pr_auc: float,
    precision_val: float,
    recall_val: float,
    f1_val: float,
    n_estimators: int,
    dataset_size: int,
    feature_count: int,
    notes: str = "",
) -> Dict[str, Any]:
    """Register a newly trained model version."""
    db = SessionLocal()
    try:
        count = db.query(ModelRegistry).count()
        version = f"v{count + 1}"
        
        now = _now()
        model = ModelRegistry(
            version=version,
            pkl_path=pkl_path,
            roc_auc=roc_auc,
            pr_auc=pr_auc,
            precision_val=precision_val,
            recall_val=recall_val,
            f1_val=f1_val,
            n_estimators=n_estimators,
            training_date=now[:10],
            dataset_size=dataset_size,
            feature_count=feature_count,
            notes=notes,
            is_production=False,
            is_archived=False,
            created_at=now
        )
        db.add(model)
        db.commit()
        db.refresh(model)
        
        return {
            "id": model.id,
            "version": model.version,
            "pkl_path": model.pkl_path,
            "roc_auc": model.roc_auc,
            "pr_auc": model.pr_auc,
            "precision_val": model.precision_val,
            "recall_val": model.recall_val,
            "f1_val": model.f1_val,
            "n_estimators": model.n_estimators,
            "training_date": model.training_date,
            "dataset_size": model.dataset_size,
            "feature_count": model.feature_count,
            "notes": model.notes,
            "is_production": model.is_production,
            "is_archived": model.is_archived,
            "created_at": model.created_at
        }
    finally:
        db.close()


def promote_model(db_path: Path, version: str) -> None:
    """Set the given version as the active production model."""
    db = SessionLocal()
    try:
        db.query(ModelRegistry).update({ModelRegistry.is_production: False})
        
        db.query(ModelRegistry).filter(ModelRegistry.version == version).update({ModelRegistry.is_production: True})
        
        db.commit()
    finally:
        db.close()


def archive_model(db_path: Path, version: str) -> None:
    """Archive a model (cannot archive the active production model)."""
    db = SessionLocal()
    try:
        model = db.query(ModelRegistry).filter(ModelRegistry.version == version).first()
        if model and model.is_production:
            raise ValueError("Cannot archive the active production model.")
            
        if model:
            model.is_archived = True
            db.commit()
    finally:
        db.close()

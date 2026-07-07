"""
Enterprise Case Management System.

Provides full CRUD operations for fraud investigation cases including:
- Unique case ID generation (FCS-YYYY-XXXXXX)
- Status lifecycle management
- Investigation notes with author + timestamp
- Immutable timeline/audit trail
- Priority management
- Analyst assignment
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.db import SessionLocal
from src.models import FraudCase


# ── Case constants ────────────────────────────────────────────────────────────

VALID_STATUSES = {"Open", "Investigating", "Escalated", "Resolved", "False_Positive"}
VALID_PRIORITIES = {"Low", "Medium", "High", "Critical"}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _generate_case_id(db: SessionLocal) -> str:
    """Generate a unique sequential case ID in format FCS-YYYY-XXXXXX."""
    year = datetime.now(timezone.utc).year
    prefix = f"FCS-{year}-"
    count = db.query(FraudCase).filter(FraudCase.case_id.like(f"{prefix}%")).count()
    return f"{prefix}{count + 1:06d}"


def _model_to_dict(model: FraudCase) -> Dict[str, Any]:
    """Convert a FraudCase model to a plain dict."""
    return {
        "id": model.id,
        "case_id": model.case_id,
        "prediction_log_id": model.prediction_log_id,
        "status": model.status,
        "priority": model.priority,
        "assigned_to": model.assigned_to,
        "title": model.title,
        "description": model.description,
        "evidence": model.evidence_json or [],
        "notes": model.notes_json or [],
        "timeline": model.timeline_json or [],
        "created_at": model.created_at,
        "updated_at": model.updated_at,
        "resolved_at": model.resolved_at,
    }


# ── Core CRUD ────────────────────────────────────────────────────────────────

def create_case(
    db_path: Path,
    prediction_log_id: Optional[int],
    title: str,
    description: str,
    priority: str = "Medium",
    assigned_to: Optional[str] = None,
    created_by: str = "system",
) -> Dict[str, Any]:
    """Create a new fraud investigation case."""
    if priority not in VALID_PRIORITIES:
        raise ValueError(f"Priority must be one of {VALID_PRIORITIES}")

    now = _now()
    initial_event = {
        "timestamp": now,
        "actor": created_by,
        "action": "Case Created",
        "from_status": None,
        "to_status": "Open",
        "note": f"Case opened with priority {priority}",
    }

    db = SessionLocal()
    try:
        case_id = _generate_case_id(db)
        case = FraudCase(
            case_id=case_id,
            prediction_log_id=prediction_log_id,
            status="Open",
            priority=priority,
            assigned_to=assigned_to,
            title=title,
            description=description,
            evidence_json=[],
            notes_json=[],
            timeline_json=[initial_event],
            created_at=now,
            updated_at=now
        )
        db.add(case)
        db.commit()
        db.refresh(case)
        return _model_to_dict(case)
    finally:
        db.close()


def get_case_by_id(db_path: Path, case_row_id: int) -> Optional[Dict[str, Any]]:
    """Fetch a single case by its integer primary key."""
    db = SessionLocal()
    try:
        case = db.query(FraudCase).filter(FraudCase.id == case_row_id).first()
        return _model_to_dict(case) if case else None
    finally:
        db.close()


def get_case_by_case_id(db_path: Path, case_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a single case by its human-readable case_id (FCS-YYYY-XXXXXX)."""
    db = SessionLocal()
    try:
        case = db.query(FraudCase).filter(FraudCase.case_id == case_id).first()
        return _model_to_dict(case) if case else None
    finally:
        db.close()


def list_cases(
    db_path: Path,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    assigned_to: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """List fraud cases with optional filters."""
    db = SessionLocal()
    try:
        query = db.query(FraudCase)
        
        if status:
            query = query.filter(FraudCase.status == status)
        if priority:
            query = query.filter(FraudCase.priority == priority)
        if assigned_to:
            query = query.filter(FraudCase.assigned_to == assigned_to)
        if search:
            query = query.filter(
                (FraudCase.title.like(f"%{search}%")) |
                (FraudCase.description.like(f"%{search}%")) |
                (FraudCase.case_id.like(f"%{search}%"))
            )
            
        cases = query.order_by(FraudCase.created_at.desc()).limit(limit).offset(offset).all()
        return [_model_to_dict(c) for c in cases]
    finally:
        db.close()


def update_case_status(
    db_path: Path,
    case_id: str,
    new_status: str,
    actor: str,
    reason: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Update the status of a case and append an event to its timeline."""
    if new_status not in VALID_STATUSES:
        raise ValueError(f"Status must be one of {VALID_STATUSES}")

    db = SessionLocal()
    try:
        case = db.query(FraudCase).filter(FraudCase.case_id == case_id).first()
        if not case:
            return None
            
        old_status = case.status
        now = _now()
        
        event = {
            "timestamp": now,
            "actor": actor,
            "action": "Status Updated",
            "from_status": old_status,
            "to_status": new_status,
            "note": reason or f"Status changed from {old_status} to {new_status}",
        }
        
        timeline = list(case.timeline_json or [])
        timeline.append(event)
        
        case.status = new_status
        case.timeline_json = timeline
        case.updated_at = now
        if new_status in ("Resolved", "False_Positive"):
            case.resolved_at = now
            
        db.commit()
        db.refresh(case)
        return _model_to_dict(case)
    finally:
        db.close()


def add_note(
    db_path: Path,
    case_id: str,
    author: str,
    content: str,
) -> Optional[Dict[str, Any]]:
    """Add an investigation note to a case."""
    db = SessionLocal()
    try:
        case = db.query(FraudCase).filter(FraudCase.case_id == case_id).first()
        if not case:
            return None
            
        now = _now()
        notes = list(case.notes_json or [])
        note = {"id": len(notes) + 1, "author": author, "content": content, "timestamp": now}
        notes.append(note)
        
        event = {
            "timestamp": now,
            "actor": author,
            "action": "Note Added",
            "from_status": case.status,
            "to_status": case.status,
            "note": f"Investigation note added by {author}",
        }
        timeline = list(case.timeline_json or [])
        timeline.append(event)
        
        case.notes_json = notes
        case.timeline_json = timeline
        case.updated_at = now
        
        db.commit()
        db.refresh(case)
        return _model_to_dict(case)
    finally:
        db.close()


def assign_case(
    db_path: Path,
    case_id: str,
    assigned_to: str,
    actor: str,
) -> Optional[Dict[str, Any]]:
    """Assign a case to an analyst."""
    db = SessionLocal()
    try:
        case = db.query(FraudCase).filter(FraudCase.case_id == case_id).first()
        if not case:
            return None
            
        now = _now()
        event = {
            "timestamp": now,
            "actor": actor,
            "action": "Assigned",
            "from_status": case.status,
            "to_status": case.status,
            "note": f"Assigned to analyst: {assigned_to}",
        }
        timeline = list(case.timeline_json or [])
        timeline.append(event)
        
        case.assigned_to = assigned_to
        case.timeline_json = timeline
        case.updated_at = now
        
        db.commit()
        db.refresh(case)
        return _model_to_dict(case)
    finally:
        db.close()


def get_case_stats(db_path: Path) -> Dict[str, Any]:
    """Return aggregate stats for the case management dashboard."""
    db = SessionLocal()
    try:
        from sqlalchemy import func
        
        status_counts_raw = db.query(FraudCase.status, func.count(FraudCase.id)).group_by(FraudCase.status).all()
        status_counts = {status: count for status, count in status_counts_raw}
        
        priority_counts_raw = db.query(FraudCase.priority, func.count(FraudCase.id)).group_by(FraudCase.priority).all()
        priority_counts = {priority: count for priority, count in priority_counts_raw}
        
        resolved = db.query(FraudCase).filter(FraudCase.resolved_at != None).count()
        total = db.query(FraudCase).count()
        
        return {
            "total": total,
            "resolved": resolved,
            "open": status_counts.get("Open", 0),
            "investigating": status_counts.get("Investigating", 0),
            "escalated": status_counts.get("Escalated", 0),
            "false_positive": status_counts.get("False_Positive", 0),
            "by_status": status_counts,
            "by_priority": priority_counts,
        }
    finally:
        db.close()

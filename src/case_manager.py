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

from src.application.ports.uow import AbstractUnitOfWork
from src.models import FraudCase


# ── Case constants ────────────────────────────────────────────────────────────

VALID_STATUSES = {"Open", "Investigating", "Escalated", "Resolved", "False_Positive"}
VALID_PRIORITIES = {"Low", "Medium", "High", "Critical"}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _generate_case_id(uow: AbstractUnitOfWork) -> str:
    """Generate a unique sequential case ID in format FCS-YYYY-XXXXXX."""
    year = datetime.now(timezone.utc).year
    prefix = f"FCS-{year}-"
    # For now, we can use the session directly from the repo for this specific query
    count = uow.fraud_cases.session.query(FraudCase).filter(FraudCase.case_id.like(f"{prefix}%")).count()
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
    uow: AbstractUnitOfWork,
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

    with uow:
        case_id = _generate_case_id(uow)
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
        uow.fraud_cases.add(case)
        uow.commit()
        return _model_to_dict(case)


def get_case_by_id(uow: AbstractUnitOfWork, case_row_id: int) -> Optional[Dict[str, Any]]:
    """Fetch a single case by its integer primary key."""
    with uow:
        case = uow.fraud_cases.get(case_row_id)
        return _model_to_dict(case) if case else None


def get_case_by_case_id(uow: AbstractUnitOfWork, case_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a single case by its human-readable case_id (FCS-YYYY-XXXXXX)."""
    with uow:
        case = uow.fraud_cases.get_by_case_id(case_id)
        return _model_to_dict(case) if case else None


def list_cases(
    uow: AbstractUnitOfWork,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    assigned_to: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """List fraud cases with optional filters."""
    with uow:
        query = uow.fraud_cases.session.query(FraudCase)
        
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


def update_case_status(
    uow: AbstractUnitOfWork,
    case_id: str,
    new_status: str,
    actor: str,
    reason: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Update the status of a case and append an event to its timeline."""
    if new_status not in VALID_STATUSES:
        raise ValueError(f"Status must be one of {VALID_STATUSES}")

    with uow:
        case = uow.fraud_cases.get_by_case_id(case_id)
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
            
        uow.commit()
        return _model_to_dict(case)


def add_note(
    uow: AbstractUnitOfWork,
    case_id: str,
    author: str,
    content: str,
) -> Optional[Dict[str, Any]]:
    """Add an investigation note to a case."""
    with uow:
        case = uow.fraud_cases.get_by_case_id(case_id)
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
        
        uow.commit()
        return _model_to_dict(case)


def assign_case(
    uow: AbstractUnitOfWork,
    case_id: str,
    assigned_to: str,
    actor: str,
) -> Optional[Dict[str, Any]]:
    """Assign a case to an analyst."""
    with uow:
        case = uow.fraud_cases.get_by_case_id(case_id)
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
        
        uow.commit()
        return _model_to_dict(case)


def get_case_stats(uow: AbstractUnitOfWork) -> Dict[str, Any]:
    """Return aggregate stats for the case management dashboard."""
    with uow:
        from sqlalchemy import func
        db = uow.fraud_cases.session
        
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


def get_sla_metrics(uow: AbstractUnitOfWork) -> Dict[str, Any]:
    """Calculate SLA compliance and breach metrics for active cases."""
    sla_hours = {"Critical": 4, "High": 12, "Medium": 24, "Low": 48}
    now_dt = datetime.now(timezone.utc)
    
    with uow:
        open_cases = uow.fraud_cases.session.query(FraudCase).filter(
            FraudCase.status.in_(["Open", "Investigating", "Escalated"])
        ).all()
        
        breached_count = 0
        breached_cases = []
        
        for case in open_cases:
            try:
                created_dt = datetime.fromisoformat(case.created_at)
                if created_dt.tzinfo is None:
                    created_dt = created_dt.replace(tzinfo=timezone.utc)
                age_hours = (now_dt - created_dt).total_seconds() / 3600.0
                max_allowed = sla_hours.get(case.priority, 24)
                
                if age_hours > max_allowed:
                    breached_count += 1
                    breached_cases.append({
                        "case_id": case.case_id,
                        "priority": case.priority,
                        "age_hours": round(age_hours, 1),
                        "sla_limit_hours": max_allowed,
                    })
            except (ValueError, TypeError):
                pass
                
        total_open = len(open_cases)
        compliance_pct = round(100.0 * (1.0 - (breached_count / total_open)), 1) if total_open > 0 else 100.0
        
        return {
            "total_active_cases": total_open,
            "breached_count": breached_count,
            "compliance_percentage": compliance_pct,
            "breached_cases": breached_cases,
        }

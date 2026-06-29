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

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


# ── Case constants ────────────────────────────────────────────────────────────

VALID_STATUSES = {"Open", "Investigating", "Escalated", "Resolved", "False_Positive"}
VALID_PRIORITIES = {"Low", "Medium", "High", "Critical"}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect(db_path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(db_path, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con


def _generate_case_id(cur: sqlite3.Cursor) -> str:
    """Generate a unique sequential case ID in format FCS-YYYY-XXXXXX."""
    year = datetime.now(timezone.utc).year
    cur.execute(
        "SELECT COUNT(*) FROM fraud_cases WHERE case_id LIKE ?",
        (f"FCS-{year}-%",),
    )
    count = cur.fetchone()[0] + 1
    return f"FCS-{year}-{count:06d}"


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    """Convert a sqlite3.Row to a plain dict with parsed JSON fields."""
    d = dict(row)
    for field in ("evidence_json", "notes_json", "timeline_json"):
        if field in d and d[field]:
            try:
                d[field.replace("_json", "")] = json.loads(d[field])
            except (json.JSONDecodeError, TypeError):
                d[field.replace("_json", "")] = []
        else:
            d[field.replace("_json", "")] = []
    return d


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
    """
    Create a new fraud investigation case.

    Args:
        db_path: Path to SQLite database.
        prediction_log_id: Optional FK to prediction_logs.
        title: Short case title.
        description: Detailed description.
        priority: One of Low / Medium / High / Critical.
        assigned_to: Analyst username (optional).
        created_by: Who created the case (for audit trail).

    Returns:
        The created case as a dict.

    Raises:
        ValueError: If priority is not valid.
    """
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

    con = _connect(db_path)
    cur = con.cursor()

    case_id = _generate_case_id(cur)
    cur.execute(
        """
        INSERT INTO fraud_cases
            (case_id, prediction_log_id, status, priority, assigned_to,
             title, description, evidence_json, notes_json, timeline_json,
             created_at, updated_at)
        VALUES (?, ?, 'Open', ?, ?, ?, ?, '[]', '[]', ?, ?, ?)
        """,
        (
            case_id,
            prediction_log_id,
            priority,
            assigned_to,
            title,
            description,
            json.dumps([initial_event]),
            now,
            now,
        ),
    )
    con.commit()
    row_id = cur.lastrowid
    con.close()

    return get_case_by_id(db_path, row_id)


def get_case_by_id(db_path: Path, case_row_id: int) -> Optional[Dict[str, Any]]:
    """Fetch a single case by its integer primary key."""
    con = _connect(db_path)
    cur = con.cursor()
    cur.execute("SELECT * FROM fraud_cases WHERE id = ?", (case_row_id,))
    row = cur.fetchone()
    con.close()
    return _row_to_dict(row) if row else None


def get_case_by_case_id(db_path: Path, case_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a single case by its human-readable case_id (FCS-YYYY-XXXXXX)."""
    con = _connect(db_path)
    cur = con.cursor()
    cur.execute("SELECT * FROM fraud_cases WHERE case_id = ?", (case_id,))
    row = cur.fetchone()
    con.close()
    return _row_to_dict(row) if row else None


def list_cases(
    db_path: Path,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    assigned_to: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """
    List fraud cases with optional filters.

    Args:
        db_path: Path to SQLite DB.
        status: Filter by case status (Open, Investigating, etc.).
        priority: Filter by priority.
        assigned_to: Filter by analyst username.
        search: Search in title or description.
        limit: Max rows to return.
        offset: Pagination offset.

    Returns:
        List of case dicts, newest first.
    """
    clauses: List[str] = []
    params: List[Any] = []

    if status:
        clauses.append("status = ?")
        params.append(status)
    if priority:
        clauses.append("priority = ?")
        params.append(priority)
    if assigned_to:
        clauses.append("assigned_to = ?")
        params.append(assigned_to)
    if search:
        clauses.append("(title LIKE ? OR description LIKE ? OR case_id LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    query = f"""
        SELECT * FROM fraud_cases
        {where}
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
    """
    params.extend([limit, offset])

    con = _connect(db_path)
    cur = con.cursor()
    cur.execute(query, params)
    rows = cur.fetchall()
    con.close()
    return [_row_to_dict(r) for r in rows]


def update_case_status(
    db_path: Path,
    case_id: str,
    new_status: str,
    actor: str,
    reason: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Update the status of a case and append an event to its timeline.

    Args:
        db_path: Path to SQLite DB.
        case_id: Human-readable case ID.
        new_status: Target status.
        actor: Username performing the action.
        reason: Optional reason for status change.

    Returns:
        Updated case dict, or None if case not found.

    Raises:
        ValueError: If new_status is not valid.
    """
    if new_status not in VALID_STATUSES:
        raise ValueError(f"Status must be one of {VALID_STATUSES}")

    case = get_case_by_case_id(db_path, case_id)
    if not case:
        return None

    old_status = case["status"]
    now = _now()

    event = {
        "timestamp": now,
        "actor": actor,
        "action": "Status Updated",
        "from_status": old_status,
        "to_status": new_status,
        "note": reason or f"Status changed from {old_status} to {new_status}",
    }

    timeline = case.get("timeline", [])
    timeline.append(event)

    resolved_at = now if new_status in ("Resolved", "False_Positive") else None

    con = _connect(db_path)
    cur = con.cursor()
    cur.execute(
        """
        UPDATE fraud_cases
        SET status = ?, timeline_json = ?, updated_at = ?, resolved_at = ?
        WHERE case_id = ?
        """,
        (new_status, json.dumps(timeline), now, resolved_at, case_id),
    )
    con.commit()
    con.close()

    return get_case_by_case_id(db_path, case_id)


def add_note(
    db_path: Path,
    case_id: str,
    author: str,
    content: str,
) -> Optional[Dict[str, Any]]:
    """
    Add an investigation note to a case.

    Args:
        db_path: Path to SQLite DB.
        case_id: Human-readable case ID.
        author: Username of the note author.
        content: Note content text.

    Returns:
        Updated case dict, or None if case not found.
    """
    case = get_case_by_case_id(db_path, case_id)
    if not case:
        return None

    now = _now()
    note = {"id": len(case.get("notes", [])) + 1, "author": author, "content": content, "timestamp": now}
    notes = case.get("notes", [])
    notes.append(note)

    event = {
        "timestamp": now,
        "actor": author,
        "action": "Note Added",
        "from_status": case["status"],
        "to_status": case["status"],
        "note": f"Investigation note added by {author}",
    }
    timeline = case.get("timeline", [])
    timeline.append(event)

    con = _connect(db_path)
    cur = con.cursor()
    cur.execute(
        "UPDATE fraud_cases SET notes_json = ?, timeline_json = ?, updated_at = ? WHERE case_id = ?",
        (json.dumps(notes), json.dumps(timeline), now, case_id),
    )
    con.commit()
    con.close()

    return get_case_by_case_id(db_path, case_id)


def assign_case(
    db_path: Path,
    case_id: str,
    assigned_to: str,
    actor: str,
) -> Optional[Dict[str, Any]]:
    """Assign a case to an analyst."""
    case = get_case_by_case_id(db_path, case_id)
    if not case:
        return None

    now = _now()
    event = {
        "timestamp": now,
        "actor": actor,
        "action": "Assigned",
        "from_status": case["status"],
        "to_status": case["status"],
        "note": f"Assigned to analyst: {assigned_to}",
    }
    timeline = case.get("timeline", [])
    timeline.append(event)

    con = _connect(db_path)
    cur = con.cursor()
    cur.execute(
        "UPDATE fraud_cases SET assigned_to = ?, timeline_json = ?, updated_at = ? WHERE case_id = ?",
        (assigned_to, json.dumps(timeline), now, case_id),
    )
    con.commit()
    con.close()

    return get_case_by_case_id(db_path, case_id)


def get_case_stats(db_path: Path) -> Dict[str, Any]:
    """Return aggregate stats for the case management dashboard."""
    con = _connect(db_path)
    cur = con.cursor()

    cur.execute("SELECT status, COUNT(*) as cnt FROM fraud_cases GROUP BY status")
    status_counts = {row["status"]: row["cnt"] for row in cur.fetchall()}

    cur.execute("SELECT priority, COUNT(*) as cnt FROM fraud_cases GROUP BY priority")
    priority_counts = {row["priority"]: row["cnt"] for row in cur.fetchall()}

    cur.execute("SELECT COUNT(*) as cnt FROM fraud_cases WHERE resolved_at IS NOT NULL")
    resolved = cur.fetchone()["cnt"]

    cur.execute("SELECT COUNT(*) as cnt FROM fraud_cases")
    total = cur.fetchone()["cnt"]

    con.close()
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

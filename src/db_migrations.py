"""
Enterprise Database Migration Manager.

Runs idempotent migrations at startup. Never drops data.
Each migration is detected by checking existing schema before applying.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import List, Tuple


def _columns(cur: sqlite3.Cursor, table: str) -> List[str]:
    """Return list of column names for a given table."""
    cur.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cur.fetchall()]


def _tables(cur: sqlite3.Cursor) -> List[str]:
    """Return list of existing table names."""
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return [row[0] for row in cur.fetchall()]


def _add_column_if_missing(
    cur: sqlite3.Cursor,
    table: str,
    column: str,
    definition: str,
) -> None:
    """Safely add a column to a table if it does not already exist."""
    if column not in _columns(cur, table):
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def run_migrations(db_path: Path) -> None:
    """
    Execute all pending schema migrations in order.

    This function is idempotent — safe to call on every application startup.
    Migrations only add tables/columns; they never drop or rename existing schema.

    Args:
        db_path: Absolute path to the SQLite database file.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path, check_same_thread=False)
    cur = con.cursor()
    cur.execute("PRAGMA journal_mode=WAL")

    existing = _tables(cur)

    # ── M001: Core prediction_logs (original table) ──────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS prediction_logs (
            id                      INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at              TEXT NOT NULL,
            transaction_json        TEXT NOT NULL,
            ml_probability          REAL NOT NULL,
            ml_risk_level           TEXT NOT NULL,
            ml_risk_score           INTEGER NOT NULL,
            final_risk_level        TEXT NOT NULL,
            final_risk_score        INTEGER NOT NULL,
            policy_override_applied INTEGER NOT NULL,
            policy_reasons_json     TEXT NOT NULL,
            suspicious_signal_count INTEGER,
            alert_json              TEXT
        )
    """)
    _add_column_if_missing(cur, "prediction_logs", "status",
                           "TEXT NOT NULL DEFAULT 'APPROVED'")

    # ── M002: Users & Authentication ─────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT UNIQUE NOT NULL,
            email         TEXT,
            password_hash TEXT NOT NULL,
            role          TEXT NOT NULL DEFAULT 'Viewer',
            is_active     INTEGER NOT NULL DEFAULT 1,
            created_at    TEXT NOT NULL,
            last_login    TEXT
        )
    """)

    # ── M003: Audit Logs ─────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            username       TEXT NOT NULL,
            action         TEXT NOT NULL,
            entity_type    TEXT,
            entity_id      TEXT,
            old_value_json TEXT,
            new_value_json TEXT,
            ip_address     TEXT DEFAULT '127.0.0.1',
            reason         TEXT,
            timestamp      TEXT NOT NULL
        )
    """)

    # ── M004: Fraud Cases ────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS fraud_cases (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id             TEXT UNIQUE NOT NULL,
            prediction_log_id   INTEGER,
            status              TEXT NOT NULL DEFAULT 'Open',
            priority            TEXT NOT NULL DEFAULT 'Medium',
            assigned_to         TEXT,
            title               TEXT NOT NULL,
            description         TEXT,
            evidence_json       TEXT DEFAULT '[]',
            notes_json          TEXT DEFAULT '[]',
            timeline_json       TEXT DEFAULT '[]',
            created_at          TEXT NOT NULL,
            updated_at          TEXT NOT NULL,
            resolved_at         TEXT,
            FOREIGN KEY(prediction_log_id) REFERENCES prediction_logs(id)
        )
    """)

    # ── M005: Business Rules Engine ──────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS business_rules (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT UNIQUE NOT NULL,
            description     TEXT NOT NULL DEFAULT '',
            rule_type       TEXT NOT NULL DEFAULT 'threshold',
            condition_json  TEXT NOT NULL DEFAULT '{}',
            action          TEXT NOT NULL DEFAULT 'flag',
            risk_level_bump TEXT NOT NULL DEFAULT 'MEDIUM',
            priority        INTEGER NOT NULL DEFAULT 50,
            is_active       INTEGER NOT NULL DEFAULT 1,
            triggered_count INTEGER NOT NULL DEFAULT 0,
            created_at      TEXT NOT NULL,
            updated_at      TEXT NOT NULL
        )
    """)

    # ── M006: Model Registry ─────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS model_registry (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            version       TEXT UNIQUE NOT NULL,
            pkl_path      TEXT NOT NULL,
            roc_auc       REAL,
            pr_auc        REAL,
            precision_val REAL,
            recall_val    REAL,
            f1_val        REAL,
            n_estimators  INTEGER,
            training_date TEXT NOT NULL,
            dataset_size  INTEGER,
            feature_count INTEGER,
            notes         TEXT,
            is_production INTEGER NOT NULL DEFAULT 0,
            is_archived   INTEGER NOT NULL DEFAULT 0,
            created_at    TEXT NOT NULL
        )
    """)

    # ── M007: Drift Snapshots ────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS drift_snapshots (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_date   TEXT NOT NULL,
            feature_name    TEXT NOT NULL,
            psi_score       REAL NOT NULL,
            alert_triggered INTEGER NOT NULL DEFAULT 0,
            baseline_mean   REAL,
            current_mean    REAL,
            baseline_std    REAL,
            current_std     REAL,
            created_at      TEXT NOT NULL
        )
    """)

    # ── M008: Customer Profiles ──────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS customer_profiles (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id           TEXT UNIQUE NOT NULL,
            total_transactions    INTEGER NOT NULL DEFAULT 0,
            fraud_count           INTEGER NOT NULL DEFAULT 0,
            avg_amount            REAL NOT NULL DEFAULT 0.0,
            max_amount            REAL NOT NULL DEFAULT 0.0,
            risk_score_avg        REAL NOT NULL DEFAULT 0.0,
            last_transaction_at   TEXT,
            first_transaction_at  TEXT,
            risk_trend            TEXT NOT NULL DEFAULT 'STABLE',
            device_count          INTEGER NOT NULL DEFAULT 1,
            country_count         INTEGER NOT NULL DEFAULT 1,
            updated_at            TEXT NOT NULL
        )
    """)

    # ── M009: Analyst Metrics ────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS analyst_metrics (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            username            TEXT NOT NULL,
            cases_resolved      INTEGER NOT NULL DEFAULT 0,
            avg_resolution_mins REAL NOT NULL DEFAULT 0.0,
            false_positive_count INTEGER NOT NULL DEFAULT 0,
            true_positive_count INTEGER NOT NULL DEFAULT 0,
            cases_escalated     INTEGER NOT NULL DEFAULT 0,
            period              TEXT NOT NULL,
            updated_at          TEXT NOT NULL
        )
    """)

    # ── M010: LLM Copilot Audit Logs ────────────────────────────────────────
    # Every LLM query + response is logged for regulatory compliance.
    # LLM outputs that influence financial decisions must be fully traceable.
    cur.execute("""
        CREATE TABLE IF NOT EXISTS copilot_logs (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id             TEXT,
            prediction_log_id   INTEGER,
            query_context_json  TEXT NOT NULL,
            llm_response        TEXT,
            model_used          TEXT NOT NULL DEFAULT 'claude-sonnet-4-6',
            tokens_used         INTEGER,
            latency_ms          INTEGER,
            is_cached           INTEGER NOT NULL DEFAULT 0,
            error               TEXT,
            created_at          TEXT NOT NULL
        )
    """)

    con.commit()
    con.close()

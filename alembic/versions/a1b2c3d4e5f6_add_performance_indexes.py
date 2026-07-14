"""add performance indexes

Revision ID: a1b2c3d4e5f6
Revises: fe89aee7afdd
Create Date: 2026-07-14 07:30:00.000000

Adds indexes on hot query paths identified during the audit:
- prediction_logs.created_at         (recent logs, time-range filters)
- prediction_logs.status             (filter by PENDING_REVIEW / BLOCKED / etc.)
- prediction_logs.final_risk_level   (filter by CRITICAL / HIGH / etc.)
- audit_logs.timestamp               (recent audit entries)
- audit_logs.username                (filter by actor)
- audit_logs.entity_type             (filter by entity kind)
- fraud_cases.status                 (case queue filtering)
- fraud_cases.assigned_to            (analyst workload views)
- fraud_cases.priority               (P1/P2/P3 sorting)
- drift_snapshots.feature_name       (latest-per-feature query)
- drift_snapshots.snapshot_date      (date-range drift scans)
- copilot_logs.case_id               (case-linked copilot history)
- copilot_logs.prediction_log_id     (log-linked copilot history)
- business_rules.is_active           (active-only rule evaluation)
- customer_profiles.risk_score_avg   (high-risk customer sorting)

Without these indexes, every dashboard query does a sequential scan. On a
Postgres table with 100k+ prediction_logs, this is the difference between
a 5ms and 500ms response time.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'fe89aee7afdd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add performance indexes on hot query paths."""
    # prediction_logs — the most queried table
    op.create_index(
        'ix_prediction_logs_created_at',
        'prediction_logs',
        ['created_at'],
    )
    op.create_index(
        'ix_prediction_logs_status',
        'prediction_logs',
        ['status'],
    )
    op.create_index(
        'ix_prediction_logs_final_risk_level',
        'prediction_logs',
        ['final_risk_level'],
    )
    # Composite index for the common "recent + status" dashboard query
    op.create_index(
        'ix_prediction_logs_created_at_status',
        'prediction_logs',
        ['created_at', 'status'],
    )

    # audit_logs
    op.create_index(
        'ix_audit_logs_timestamp',
        'audit_logs',
        ['timestamp'],
    )
    op.create_index(
        'ix_audit_logs_username',
        'audit_logs',
        ['username'],
    )
    op.create_index(
        'ix_audit_logs_entity_type',
        'audit_logs',
        ['entity_type'],
    )

    # fraud_cases
    op.create_index(
        'ix_fraud_cases_status',
        'fraud_cases',
        ['status'],
    )
    op.create_index(
        'ix_fraud_cases_assigned_to',
        'fraud_cases',
        ['assigned_to'],
    )
    op.create_index(
        'ix_fraud_cases_priority',
        'fraud_cases',
        ['priority'],
    )

    # drift_snapshots — used by get_latest_drift_snapshots (subquery on feature_name)
    op.create_index(
        'ix_drift_snapshots_feature_name',
        'drift_snapshots',
        ['feature_name'],
    )
    op.create_index(
        'ix_drift_snapshots_snapshot_date',
        'drift_snapshots',
        ['snapshot_date'],
    )
    # Composite for the "latest per feature" subquery
    op.create_index(
        'ix_drift_snapshots_feature_name_id',
        'drift_snapshots',
        ['feature_name', 'id'],
    )

    # copilot_logs
    op.create_index(
        'ix_copilot_logs_case_id',
        'copilot_logs',
        ['case_id'],
    )
    op.create_index(
        'ix_copilot_logs_prediction_log_id',
        'copilot_logs',
        ['prediction_log_id'],
    )

    # business_rules
    op.create_index(
        'ix_business_rules_is_active',
        'business_rules',
        ['is_active'],
    )

    # customer_profiles
    op.create_index(
        'ix_customer_profiles_risk_score_avg',
        'customer_profiles',
        ['risk_score_avg'],
    )


def downgrade() -> None:
    """Drop all indexes added in upgrade()."""
    op.drop_index('ix_customer_profiles_risk_score_avg', table_name='customer_profiles')
    op.drop_index('ix_business_rules_is_active', table_name='business_rules')
    op.drop_index('ix_copilot_logs_prediction_log_id', table_name='copilot_logs')
    op.drop_index('ix_copilot_logs_case_id', table_name='copilot_logs')
    op.drop_index('ix_drift_snapshots_feature_name_id', table_name='drift_snapshots')
    op.drop_index('ix_drift_snapshots_snapshot_date', table_name='drift_snapshots')
    op.drop_index('ix_drift_snapshots_feature_name', table_name='drift_snapshots')
    op.drop_index('ix_fraud_cases_priority', table_name='fraud_cases')
    op.drop_index('ix_fraud_cases_assigned_to', table_name='fraud_cases')
    op.drop_index('ix_fraud_cases_status', table_name='fraud_cases')
    op.drop_index('ix_audit_logs_entity_type', table_name='audit_logs')
    op.drop_index('ix_audit_logs_username', table_name='audit_logs')
    op.drop_index('ix_audit_logs_timestamp', table_name='audit_logs')
    op.drop_index('ix_prediction_logs_created_at_status', table_name='prediction_logs')
    op.drop_index('ix_prediction_logs_final_risk_level', table_name='prediction_logs')
    op.drop_index('ix_prediction_logs_status', table_name='prediction_logs')
    op.drop_index('ix_prediction_logs_created_at', table_name='prediction_logs')

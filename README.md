# Enterprise Transaction Fraud Intelligence Platform 🛡️

A production-grade, AI-powered fraud operations platform built for modern fintechs, banks, and payment processors.

This platform bridges the gap between raw Machine Learning outputs and human Compliance Operations, providing a complete 360° lifecycle for fraud intelligence: from real-time ML inference, heuristic business rules, and Explainable AI (XAI) to Case Management, Data Drift Monitoring, and Executive Analytics.

## ✨ Core Enterprise Features

### 1. Artificial Intelligence & MLOps
- **Predictive Engine:** Calibrated RandomForest (200 trees, depth 12, isotonic calibration) for transaction scoring.
- **Explainable AI (XAI):** Real `shap.TreeExplainer` feature contributions (waterfall charts) for deep transparency.
- **Model Registry:** Version control for ML models with one-click production promotion/rollback. Promotion actually changes which model serves traffic (via `/admin/reload-model`).
- **Data Drift Monitoring:** Continuous Population Stability Index (PSI) tracking against a cached training baseline. Champion/challenger gating prevents silent model downgrades.

### 2. Policy & Compliance Operations
- **Business Rules Engine:** Dynamic heuristic rules (e.g., Velocity, Impossible Travel) that override or augment ML scores. Rules are evaluated against every prediction and merged into the final risk assessment.
- **Case Management System:** Full investigative queue with timelines, internal notes, and assignment (Open, Investigating, Escalated, Resolved).
- **LLM Copilot (AIOps):** Natural language transaction explanations and chat support powered by Claude (`claude-sonnet-4-5`), strictly constrained to database context.
- **Role-Based Access Control (RBAC):** Secure access tiers (Admin, Fraud_Analyst, Compliance_Officer, Auditor, Viewer) with bcrypt-hashed passwords.
- **Immutable Audit Logs:** Strict tracking of every action (status changes, model deployments, rule creation, and all LLM Copilot queries) for regulatory compliance.

## Architecture

- **Backend:** FastAPI + SQLAlchemy ORM + Alembic migrations + PostgreSQL (SQLite fallback for dev)
- **Frontend (new):** Next.js 16 + TypeScript + Tailwind CSS 4 + shadcn/ui — the **Sentinel** UI (dark cyber-fintech theme)
- **Frontend (legacy):** Streamlit dashboard (still maintained for backward compat)
- **ML Layer:** Scikit-Learn (RandomForest), MLflow tracking, SHAP for explainability, isotonic calibration
- **CI/CD:** GitHub Actions for automated pytest, lint, Docker builds, Trivy + pip-audit security scanning

## Local Development

### Prerequisites
- Python 3.12+ (matches Dockerfile + CI)
- 8GB RAM minimum
- Anthropic API Key (for LLM Copilot)
- PostgreSQL 16 (or use Docker)

### Option 1: Docker (recommended)

```bash
# 1. Copy env template
cp .env.example .env
# Edit .env: set POSTGRES_PASSWORD, ANTHROPIC_API_KEY, API_AUTH_TOKEN, etc.

# 2. Start the stack (Postgres + API + Streamlit + MLflow)
docker compose up -d

# 3. Run database migrations
docker compose exec api alembic upgrade head

# 4. Seed demo data (optional — set SEED_DEMO_USERS=1 in .env first)
docker compose exec api python scripts/seed_enterprise_data.py
```

### Option 2: Local Python (without Docker)

```bash
# 1. Install dependencies (versions are pinned for reproducibility)
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env:
#   DATABASE_URL=postgresql://user:pass@localhost:5432/fraud_intelligence
#   ANTHROPIC_API_KEY=your-key-here
#   API_AUTH_TOKEN=your-secure-api-token
#   CORS_ORIGINS=http://localhost:8501,http://localhost:3000
#   SEED_DEMO_USERS=1   # set to 0 in production

# 3. Run migrations
alembic upgrade head

# 4. (Optional) Seed demo data
SEED_DEMO_USERS=1 python scripts/seed_enterprise_data.py

# 5. Fetch model artifacts (DVC)
dvc pull    # fetches best_fraud_model.pkl + transaction_data.csv

# 6. Start the platform
python run.py   # launches FastAPI on :8000 + Streamlit on :8501
```

### Frontend (Sentinel UI)

The new production-grade Next.js frontend lives in `frontend/`. See `frontend/README.md` for full setup.

```bash
cd frontend
npm install
npm run dev    # starts on :3000
```

### 🔐 Demo Credentials

Demo users are ONLY seeded when `SEED_DEMO_USERS=1` is set in the environment. Passwords are read from `DEMO_USER_<NAME>_PASSWORD` env vars; if missing, a secure random password is generated and logged once.

| Username    | Role                | Env var                          |
|-------------|---------------------|----------------------------------|
| `admin`     | Admin               | `DEMO_USER_ADMIN_PASSWORD`       |
| `analyst`   | Fraud_Analyst       | `DEMO_USER_ANALYST_PASSWORD`     |
| `compliance`| Compliance_Officer  | `DEMO_USER_COMPLIANCE_PASSWORD`  |
| `auditor`   | Auditor             | `DEMO_USER_AUDITOR_PASSWORD`     |
| `viewer`    | Viewer              | `DEMO_USER_VIEWER_PASSWORD`      |

**In production:** Set `SEED_DEMO_USERS=0` (or unset) and provision real users via the database.

### Environment Variables

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | SQLAlchemy DB URL | `sqlite:///./data/app_db/fraud_intelligence.db` |
| `ANTHROPIC_API_KEY` | Anthropic API key for Copilot | (required for Copilot) |
| `ANTHROPIC_MODEL` | Claude model ID | `claude-sonnet-4-5` |
| `API_AUTH_TOKEN` | Static admin API token | (set in production) |
| `CORS_ORIGINS` | Comma-separated allowed origins | `http://localhost:8501,http://localhost:3000` |
| `SEED_DEMO_USERS` | Set to `1` to seed demo users | `0` |
| `DEMO_USER_<NAME>_PASSWORD` | Per-user demo password | (random if unset) |
| `MLFLOW_TRACKING_URI` | MLflow tracking server | `sqlite:///mlflow.db` |
| `DRIFT_CHECK_INTERVAL_MINUTES` | Drift scheduler interval | `30` |

## Model Artifacts

Large binary files and datasets are tracked using Data Version Control (DVC).

```bash
# 1. Install DVC with S3 support
pip install dvc[s3]

# 2. Configure AWS credentials
aws configure

# 3. Pull model + data
dvc pull
```

> **Note:** The current DVC remote is `/tmp/dvc-store` (local placeholder). Update via `dvc remote modify default url s3://your-bucket/dvc-store` once an S3 bucket is provisioned.

## API Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/health` | — | Health check + model version |
| POST | `/predict` | Bearer | Score a transaction |
| POST | `/debug/predict` | Bearer | Score + return engineered features |
| GET | `/logs/recent` | Bearer | Recent prediction logs |
| POST | `/admin/seed-logs` | `manage_users` | Bulk-seed logs from X_test |
| POST | `/logs/{id}/action` | `manage_cases` | Approve/Block a transaction |
| GET | `/stats` | Bearer | Aggregate stats |
| GET | `/logs/{id}/explain` | Bearer | Per-log explanation |
| POST | `/copilot/explain` | Bearer | LLM explanation |
| GET | `/copilot/logs` | `view_audit` | Copilot audit trail |
| POST | `/admin/reload-model` | `retrain_model` | Hot-reload model after promotion |

**Auth:** Send `Authorization: Bearer <API_AUTH_TOKEN>` (admin) or `Authorization: Bearer <username>:<password>` (demo convenience).

## Testing

```bash
# Run all tests with coverage
pytest -v --cov=src --cov=api --cov-report=term-missing

# Run only ML tests
pytest tests/test_rules_engine.py tests/test_retrain_trigger.py tests/test_train_pipeline.py

# Run API integration tests (requires httpx)
pytest tests/test_api.py
```

## CI/CD

GitHub Actions workflows (in `.github/workflows/`):

| Workflow | Trigger | Purpose |
|---|---|---|
| `ci.yml` | push/PR on main | Python syntax check across all files |
| `backend-ci.yml` | push/PR on main (api/src/tests/alembic) | Security scan (eval/exec) + pytest with Postgres 16 + coverage |
| `frontend-ci.yml` | push/PR on main (frontend/) | npm ci + lint + typecheck + build |
| `docker-build-push.yml` | push on main + tags `v*` | Matrix build (api/streamlit/nextjs) + push to GHCR + Trivy + pip-audit |
| `compose-integration-test.yml` | PR on main | Full `docker compose up` smoke test |

---
*Built as a showcase for production-level ML Engineering, Full-Stack Architecture, and DevOps.*

# Enterprise Transaction Fraud Intelligence Platform 🛡️

A production-grade, AI-powered fraud operations platform built for modern fintechs, banks, and payment processors.

This platform bridges the gap between raw Machine Learning outputs and human Compliance Operations, providing a complete 360° lifecycle for fraud intelligence: from real-time ML inference, heuristic business rules, and Explainable AI (XAI) to Case Management, Data Drift Monitoring, and Executive Analytics.

## ✨ Core Enterprise Features

### 1. Artificial Intelligence & MLOps
*   **Predictive Engine:** High-performance Random Forest model for transaction scoring.
*   **Explainable AI (XAI):** Real-time SHAP-like feature contributions (waterfall charts) for deep transparency.
*   **Model Registry:** Version control for ML models with one-click production promotion/rollback.
*   **Data Drift Monitoring:** Continuous Population Stability Index (PSI) tracking to detect feature drift over time.

### 2. Policy & Compliance Operations
*   **Business Rules Engine:** Dynamic heuristic rules (e.g., Velocity, Impossible Travel) that override or augment ML scores.
*   **Case Management System:** Full investigative queue with timelines, internal notes, and assignment (Open, Investigating, Escalated, Resolved).
*   **LLM Copilot (AIOps):** Natural language transaction explanations and chat support powered by Claude, strictly constrained to database context.
*   **Role-Based Access Control (RBAC):** Secure access tiers (Admin, Analyst, Executive, Data Scientist).
*   **Immutable Audit Logs:** Strict tracking of every action (status changes, model deployments, rule creation, and all LLM Copilot queries) for regulatory compliance.

### 3. Analytics & Intelligence
*   **Customer Risk 360:** Lazy-aggregated profiles showing lifetime risk scores, fraud flags, and mock device/location intelligence.
*   **Executive Dashboard:** High-level KPIs measuring revenue saved (blocked fraud) vs potential loss (approved fraud), and SLA tracking.
*   **False Positive Analytics:** Analyst leaderboard and operational waste projections to optimize alert accuracy.
*   **Live Simulator:** Real-time bursty transaction generator simulating WebSocket gateway feeds for velocity monitoring.
*   **Compliance Export Center:** CSV, Excel, and JSON data extraction for regulatory audits.

## 🚀 Getting Started

### Prerequisites
* Python 3.10+
* 8GB RAM minimum (Optimized for standard dev environments)
* Anthropic API Key (for LLM Copilot)

### Model Artifacts

Large binary files and datasets are tracked using Data Version Control (DVC).

To fetch the artifacts:
1. Ensure DVC is installed (`pip install dvc[s3]`).
2. Configure AWS credentials (e.g. `aws configure`).
3. Run `dvc pull` to fetch the `best_fraud_model.pkl` and datasets.

*Note: The current remote is configured as a local placeholder. Once an S3 bucket is provisioned, the remote should be updated via `dvc remote modify default url s3://your-bucket-name/dvc-store`.*

## Installation
1. Clone the repository and install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables:
Create a `.env` file in the root directory (refer to `.env.example`) and add your API key:
```env
ANTHROPIC_API_KEY=your-api-key-here
```

2. Generate Demo Data & Migrations (Enterprise Seeder):
```bash
python scripts/seed_enterprise_data.py
```
*(This idempotently builds the DB schema, seeds 25 historic cases, 50 audit logs, 8 active business rules, and creates 4 demo users).*

3. Run the Platform:
```bash
python run.py
```
*(This launches both the FastAPI backend on port 8000 and the Streamlit UI on port 8501).*

### 🔐 Demo Credentials
Access the portal at `http://localhost:8501` using one of the seeded accounts:
*   **Admin/Exec:** `admin` / `admin123`
*   **Data Scientist:** `ds_user` / `ds_123`
*   **Senior Analyst:** `analyst_sr` / `analyst_123`
*   **Junior Analyst:** `analyst_jr` / `analyst_123`

---
*Built as a showcase for production-level ML Engineering, Full-Stack Architecture, and DevOps.*
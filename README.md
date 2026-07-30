# Enterprise Transaction Fraud Intelligence Platform 🛡️⚡

[![CI Pipeline](https://github.com/prince3235/transaction-fraud-intelligence/actions/workflows/ci.yml/badge.svg)](https://github.com/prince3235/transaction-fraud-intelligence/actions/workflows/ci.yml)
[![Python Version](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.103+-009688.svg)](https://fastapi.tiangolo.com/)
[![Next.js 16](https://img.shields.io/badge/Next.js-16.1-black.svg)](https://nextjs.org/)
[![Redis](https://img.shields.io/badge/Redis-7.0-red.svg)](https://redis.io/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue.svg)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A **production-grade, AI-powered fraud decisioning and intelligence platform** built for modern fintechs, banks, and enterprise payment processors. 

This platform bridges the gap between raw Machine Learning outputs and human Compliance Operations, providing a complete 360° lifecycle for real-time transaction risk scoring, multi-tenant security, Explainable AI (XAI), RAG-enhanced AI Copilot, and automated MLOps drift monitoring.

---

## 🏗️ System Architecture

```
                                 ┌────────────────────────────────────────┐
                                 │   Sentinel UI (Next.js 16 + React 19)   │
                                 └───────────────────┬────────────────────┘
                                                     │ HTTP REST / JWT
                                                     ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                       FastAPI Async Backend (:8000)                                     │
│                                                                                                        │
│  ┌───────────────────────┐   ┌───────────────────────┐   ┌───────────────────┐   ┌───────────────────┐  │
│  │ JWT & Multi-Tenant    │   │ Async ML Engine       │   │ Heuristic Rules   │   │ Compliance RAG    │  │
│  │ Organization RBAC     │   │ (RandomForest 0.991)  │   │ Engine            │   │ LLM Copilot       │  │
│  └───────────┬───────────┘   └───────────┬───────────┘   └─────────┬─────────┘   └─────────┬─────────┘  │
└──────────────┼───────────────────────────┼─────────────────────────┼─────────────────────────┼──────────┘
               │                           │                         │                         │
               ▼                           ▼                         ▼                         ▼
┌──────────────────────────────┐ ┌───────────────────┐ ┌───────────────────────────┐ ┌───────────────────┐
│ PostgreSQL 16 / SQLite ORM   │ │ Real-Time Redis   │ │ SHAP Explainability (XAI) │ │ Claude Sonnet     │
│ (SQLAlchemy Multi-Tenant)    │ │ Velocity Store    │ │ TreeExplainer             │ │ Policy Engine     │
└──────────────────────────────┘ └───────────────────┘ └───────────────────────────┘ └───────────────────┘
```

---

## ✨ Core Enterprise Features

### 1. 🤖 Advanced Machine Learning & MLOps Engine
- **High-Accuracy ML Model:** Calibrated RandomForest Classifier achieving **0.991 ROC-AUC** and **0.999 PR-AUC** trained on imbalanced financial transaction data with zero data leakage.
- **Async Non-Blocking Inference:** ML feature engineering and tree traversals offloaded to asynchronous thread executors to guarantee **sub-50ms P99 latency** under heavy concurrent traffic.
- **Explainable AI (XAI):** `SHAP.TreeExplainer` feature contribution breakdowns (waterfall charts) generated in real time to explain specific risk score drivers to compliance teams.
- **Continuous Population Drift Monitoring:** Population Stability Index (PSI) tracking against baseline training distributions. Automated champion-challenger model retraining pipeline triggered upon drift detection.

### 2. ⚡ Real-Time Redis Velocity Store (Feature Store)
- **Sliding-Window Aggregations:** Integrated `redis.asyncio` sorted sets tracking 10-minute sliding window transaction frequency (`velocity_count_10m`) and cumulative spend (`velocity_sum_10m`) per customer account.
- **Fail-Safe Fallback Guarantee:** All Redis calls feature strict non-fatal exception handling. If Redis is offline during local dev or network partitioning, the system gracefully defaults to neutral metrics without interrupting ML inference.

### 3. 🧠 GenAI Copilot with Compliance Vector RAG
- **RAG Knowledge Retrieval:** Built an in-memory **TF-IDF + Cosine Similarity Vector Retriever** indexing enterprise compliance documents (AML Account Draining SOPs, Mule Account Profiles, FinCEN SAR Filing rules).
- **Contextual LLM Explanations:** Dynamically injects relevant policy guidelines into Claude (`claude-sonnet-4-5`) prompt strings to produce regulatory-grade transaction audit summaries.

### 4. 🔒 Multi-Tenant RBAC & Security Hardening
- **JWT Bearer Authentication:** Standardized `PyJWT` authentication with HS256 signature verification, configurable token expiration, and standard `/auth/login` endpoint.
- **Multi-Tenant Organization Scoping:** `Organization` model schema with foreign key isolation across `User`, `PredictionLog`, `FraudCase`, and `BusinessRule` tables. `get_current_tenant` dependency enforces strict cross-tenant data privacy.
- **Immutable Audit Trails:** Full tracking of user actions (status changes, model deployments, rule creation, and LLM Copilot queries).

### 5. 🎨 Modern Cyber-Fintech UI (Next.js 16 Sentinel)
- **Sentinel Dashboard:** Built with Next.js 16, TypeScript, TailwindCSS, and Shadcn UI featuring real-time risk telemetry, interactive rule configuration, and case management workflows.
- **Streamlit Control Center:** Maintained secondary Streamlit dashboard for rapid internal ML model inspection and simulation workspace.

---

## 🛠️ Tech Stack & Technologies

| Layer | Technologies Used |
|---|---|
| **Backend API** | FastAPI, Python 3.12, Uvicorn, Pydantic v2 |
| **Database & ORM** | PostgreSQL 16, SQLAlchemy 2.0, Alembic, SQLite |
| **Caching & Velocity** | Redis 7, `redis.asyncio` |
| **Machine Learning** | Scikit-Learn, Pandas, NumPy, SHAP, MLflow |
| **AI & LLM** | Anthropic Claude API, TF-IDF RAG Vectorization |
| **Frontend UI** | Next.js 16, React 19, TypeScript, TailwindCSS |
| **DevOps & CI/CD** | Docker, GitHub Actions (Postgres & Redis Services), Pytest |

---

## 🚀 Quick Start Guide

### Prerequisites
- Python 3.12+
- Node.js 20+
- Git

### 1. Clone & Set Up Environment

```bash
git clone https://github.com/prince3235/transaction-fraud-intelligence.git
cd transaction-fraud-intelligence

# Create virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install backend dependencies
pip install -r requirements.txt
```

### 2. Seed Enterprise Demo Data

Populate the database with demo users, business rules, and sample fraud cases:

```bash
# Set environment variables for demo mode
# On Windows (PowerShell):
$env:SEED_DEMO_USERS="1"
$env:API_AUTH_TOKEN="test-admin-token-12345"

# Run enterprise data seeder
python scripts/seed_enterprise_data.py
```

### 3. Run the Platform

Launch both FastAPI Backend (`:8000`) and Next.js Sentinel UI (`:3000`) concurrently using the single stack launcher:

```bash
python run_node_stack.py
```

- 🌐 **Sentinel Web UI:** [http://localhost:3000](http://localhost:3000)
- ⚡ **FastAPI Swagger API Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🔐 Enterprise Demo Credentials

Login at [http://localhost:3000](http://localhost:3000):

| Username | Password | Role | Access Level |
|---|---|---|---|
| `admin` | `admin123` | Admin | Full System Access |
| `analyst` | `analyst123` | Fraud_Analyst | Alert Queue & Case Management |
| `compliance` | `comply123` | Compliance_Officer | Audit Logs & Compliance RAG |
| `auditor` | `audit123` | Auditor | Read-only Audit Compliance |
| `viewer` | `view123` | Viewer | Dashboard Analytics Only |

---

## 🧪 Testing & Verification

Run the full automated unit and integration test suite (43+ passing tests):

```bash
# Run complete test suite
pytest -v

# Run with test coverage report
pytest --cov=src --cov=api --cov-report=term-missing
```

---

## 📡 API Overview

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/auth/login` | — | Authenticate user & return JWT Bearer token |
| `GET` | `/health` | — | API health check & active ML model version |
| `POST` | `/predict` | Bearer | Async transaction scoring with ML & rules |
| `POST` | `/debug/predict` | Bearer | Transaction scoring + full engineered features |
| `GET` | `/logs/recent` | Bearer | Fetch tenant-scoped prediction logs |
| `POST` | `/logs/{id}/action` | Bearer | Update case resolution (Approve/Block) |
| `GET` | `/stats` | Bearer | Real-time transaction risk telemetry |
| `POST` | `/copilot/explain` | Bearer | LLM RAG explanation for flagged transaction |

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

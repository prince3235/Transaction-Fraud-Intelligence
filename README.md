# 🛡️ Transaction Fraud Intelligence System

**End-to-end ML-powered fraud detection platform with real-time risk scoring, policy-based alerts, explainability, and premium monitoring dashboard.**

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-red.svg)](https://streamlit.io/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📌 Overview

The **Transaction Fraud Intelligence System** is a production-ready fraud detection platform that combines machine learning-based risk prediction with rule-based policy overrides to provide transparent, explainable, and business-aligned fraud monitoring.

Unlike traditional black-box fraud models, this system:
- ✅ Provides **explainable predictions** (why a transaction was flagged)
- ✅ Implements **business rule overrides** (policy-based risk elevation)
- ✅ Offers **real-time monitoring** via a premium SaaS-style dashboard
- ✅ Logs all predictions for **audit trails and analytics**
- ✅ Exposes **RESTful APIs** for integration and testing

---

## 🎯 Problem Statement

Financial institutions and fintech platforms face challenges in:
- Detecting fraudulent transactions in real-time
- Balancing fraud detection accuracy with false positives
- Explaining fraud decisions to analysts and customers
- Monitoring fraud trends and alert patterns

This project addresses these issues by building a **hybrid intelligence system** that combines ML predictions with configurable business rules.

---

## ✨ Key Features

### 🤖 Machine Learning Engine
- **Random Forest classifier** trained on financial transaction data
- **Feature engineering** (20+ derived features: balance errors, velocity, ratios, behavioral signals)
- **Imbalanced data handling** (undersampling + class weighting)
- **Model evaluation** (ROC-AUC, PR-AUC, Precision/Recall metrics)

### 🔒 Policy Override Engine
- **Rule-based risk elevation** (e.g., account emptying, high velocity, amount anomalies)
- **Composite risk scoring** (ML probability + business rules)
- **Alert level assignment** (Low / Medium / High / Critical)
- **Recommended actions** (Allow / Monitor / Manual Review / Hold)

### 📊 Explainability & Transparency
- **SHAP-based explanations** (global feature importance + per-transaction reasons)
- **Policy trigger reasons** (why override was applied)
- **Risk score breakdown** (ML vs Final risk comparison)

### 🌐 FastAPI Backend
- **RESTful API** for fraud prediction
- **Health, stats, and logs endpoints** for monitoring
- **Debug endpoint** with detailed feature breakdown
- **Admin endpoint** for sample data seeding
- **SQLite-based audit logging**

### 🎨 Premium Streamlit Dashboard
- **SaaS-grade UI** (dark theme, glassmorphism, smooth animations)
- **KPI cards** (total transactions, critical alerts, override rate, avg risk score)
- **Interactive charts** (risk distribution, alert trends over time)
- **Transaction explorer** (sortable table with 9K+ logged predictions)
- **Policy override insights** (top triggers and frequency analysis)

---

## 🏗️ System Architecture
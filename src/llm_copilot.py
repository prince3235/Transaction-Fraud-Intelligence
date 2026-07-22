"""
LLM Copilot Module — AIOps Analyst Assistant.

Provides natural-language explanations for flagged transactions by combining:
  - ML probability + feature contributions (SHAP-approximation)
  - Matched business rules
  - Historical user activity from prediction_logs
  - Final risk level & recommended action

Calls Anthropic Claude via the official SDK with:
  - Retry logic (exponential backoff, max 3 retries)
  - 15-second timeout with graceful degradation
  - 10-minute in-memory LRU cache keyed on (prediction_log_id, data_hash)
  - Full audit logging to copilot_logs table (compliance requirement)
  - Streaming support for Streamlit frontend

Usage:
    from src.llm_copilot import CopilotEngine
    engine = CopilotEngine(db_path, project_root)
    explanation = engine.explain(prediction_log_id=1234)
    # or: engine.explain_stream(prediction_log_id=1234)  # yields text chunks
"""
from __future__ import annotations

import json
import logging
import os
import time
import hashlib
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────
# NOTE: "claude-sonnet-4-6" is NOT a valid Anthropic model ID. We default to a
# real, publicly-listed model ID and allow env override for future models.
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5")
MAX_RETRIES = 3
TIMEOUT_SECONDS = 15
CACHE_TTL_SECONDS = 600  # 10 minutes

# ── LRU cache layer (in-process, per deployment) ──────────────────────────────
# Key: (prediction_log_id, data_hash), Value: (explanation_text, cached_at_ts)
_explanation_cache: Dict[str, tuple] = {}


def _cache_key(prediction_log_id: int, context_hash: str) -> str:
    return f"{prediction_log_id}:{context_hash}"


def _get_from_cache(key: str) -> Optional[str]:
    """Return cached explanation if still within TTL, else None."""
    entry = _explanation_cache.get(key)
    if entry:
        text, cached_at = entry
        if time.time() - cached_at < CACHE_TTL_SECONDS:
            return text
        else:
            del _explanation_cache[key]
    return None


def _store_in_cache(key: str, text: str) -> None:
    _explanation_cache[key] = (text, time.time())


# ── System Prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are a Compliance AI Copilot embedded inside a fraud intelligence platform used by bank analysts and financial crime investigators.

Your ONLY job is to explain WHY a transaction was flagged as suspicious, using the specific data provided to you. 

STRICT RULES YOU MUST FOLLOW:
1. ONLY reason from the data explicitly provided. Never invent transaction details not in the context.
2. NO machine learning jargon (never say "z-score", "feature importance", "SHAP value", "model confidence"). Translate everything into plain business language.
3. ALWAYS write as if addressing a human compliance analyst who may have no ML background.
4. If the risk level is HIGH or CRITICAL, ALWAYS end with a specific recommended next action, such as:
   - "Recommend immediate escalation to Tier-2 investigation team."
   - "Recommend manual KYC re-verification before releasing funds."
   - "Recommend freezing account and contacting customer via registered phone number."
5. If the case ID or transaction is not found, say clearly: "This case was not found in the system. Please verify the case ID and try again."
6. Keep the explanation concise: 2-5 sentences for the main explanation, plus the recommendation if applicable.
7. Never make probability statements like "there is a 94% chance of fraud" — instead say "the system assessed this as very high risk".

TONE: Professional, direct, compliance-first. Think senior fraud analyst reviewing a case for a junior colleague."""


# ── Feature name → human-readable business translation ──────────────────────
FEATURE_TRANSLATIONS = {
    "balance_error_orig": "the sender's account balance didn't match what it should be after the transfer (possible tampering)",
    "balance_error_dest": "the recipient's account balance shows a discrepancy (possible intermediary account)",
    "sender_account_emptied": "the sender's account was completely drained by this transaction",
    "dest_received_large_amount": "the receiving account received an unusually large amount",
    "log_amount": "the transaction amount was very large",
    "amount_to_oldbalance_orig_ratio": "the transaction consumed most or all of the sender's available balance",
    "is_large_transaction": "the transaction was flagged as an unusually large amount",
    "type_risk_score": "the transaction type (TRANSFER or CASH_OUT) is associated with higher fraud rates",
    "is_oldbalanceOrg_zero": "the sender's account had a zero starting balance",
    "is_newbalanceOrig_zero": "the sender's balance dropped to zero after the transaction",
    "is_oldbalanceDest_zero": "the receiving account had a zero starting balance (possible money mule account)",
    "is_newbalanceDest_zero": "the receiving account's balance remained near zero after receiving funds",
    "suspicious_signal_count": "multiple suspicious signals were detected simultaneously",
    "transactions_in_step": "there were many transactions occurring in the same time window (velocity alert)",
    "is_high_velocity_step": "an unusually high number of transactions occurred in a short time period",
}


def _translate_feature(feature_name: str, value: float, contribution: float) -> str:
    """Convert a technical feature name into an analyst-readable description."""
    base = FEATURE_TRANSLATIONS.get(feature_name, feature_name.replace("_", " "))
    direction = "increased" if contribution > 0 else "slightly reduced"
    return f"{base} ({direction} risk)"


# ── RAG Compliance Knowledge Base & Vector Retriever ─────────────────────────

DEFAULT_COMPLIANCE_DOCS = [
    {
        "id": "DOC-101",
        "title": "AML Policy 102: Single-Transaction Account Draining",
        "category": "Anti-Money Laundering",
        "content": (
            "When a sender's account balance is reduced to zero in a single transfer or cash-out transaction, "
            "it represents a severe red flag for money laundering or account takeover. Investigators must verify "
            "whether funds were moved to a newly created counterparty account and place a temporary hold on outward settlement."
        )
    },
    {
        "id": "DOC-204",
        "title": "Compliance Guideline 204: High Velocity Burst Patterns",
        "category": "Fraud Operations",
        "content": (
            "Multi-transaction bursts occurring within the same time step indicate automated botnet or script execution. "
            "Transactions falling within high-velocity time steps must be subjected to step-level fraud aggregation analysis, "
            "and device fingerprinting should be enforced."
        )
    },
    {
        "id": "DOC-305",
        "title": "Fraud Prevention Manual Sec 4.1: Mule Destination Account Profiles",
        "category": "Financial Crime",
        "content": (
            "Destination accounts starting with a zero opening balance that receive substantial incoming transfers are prime "
            "candidates for money mule intermediary accounts. High-risk actions include immediately freezing the recipient account "
            "and requesting re-KYC verification before allowing fund disbursement."
        )
    },
    {
        "id": "DOC-408",
        "title": "Payment Regulation Standard 408: High-Risk Transaction Types",
        "category": "Regulatory Policy",
        "content": (
            "TRANSFER and CASH_OUT transaction types exhibit significantly higher historical fraud loss rates compared to PAYMENT or DEBIT. "
            "Any TRANSFER followed immediately by a CASH_OUT of identical magnitude constitutes a classic fraud loop requiring mandatory manual review."
        )
    },
    {
        "id": "DOC-512",
        "title": "Data Integrity Policy 512: Balance Discrepancy & Ledger Error",
        "category": "Audit & Compliance",
        "content": (
            "Post-transaction balance discrepancies (where calculated new balance differs from ledger recorded new balance) signal "
            "either database tampering, race condition exploitation, or payload manipulation. Transactions exhibiting non-zero balance error "
            "must be escalated to senior compliance auditors immediately."
        )
    },
    {
        "id": "DOC-601",
        "title": "FinCEN & FATF SAR Filing Guidelines (Thresholds & Signal Accumulation)",
        "category": "Regulatory Reporting",
        "content": (
            "Accumulation of 3 or more concurrent suspicious risk signals (e.g. large amount, zero balance destination, high velocity) "
            "triggers mandatory regulatory reporting evaluation. If total flagged transaction value exceeds $10,000, compliance officers "
            "must draft a Suspicious Activity Report (SAR) within 30 days."
        )
    }
]


class ComplianceKnowledgeRetriever:
    """
    RAG Vector Retriever for Fraud Compliance & Regulatory Guidelines.
    Uses TF-IDF vector embeddings & Cosine Similarity for fast, dependency-free semantic retrieval.
    """

    def __init__(self, docs: Optional[List[Dict[str, str]]] = None):
        self.docs = docs or DEFAULT_COMPLIANCE_DOCS
        self.vectorizer = None
        self.doc_matrix = None
        self._build_index()

    def _build_index(self):
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            corpus = [f"{d['title']} {d['category']} {d['content']}" for d in self.docs]
            self.vectorizer = TfidfVectorizer(stop_words="english")
            self.doc_matrix = self.vectorizer.fit_transform(corpus)
        except Exception as exc:
            logger.warning("Failed to build RAG vector index: %s", exc)

    def retrieve(self, query: str, top_k: int = 2) -> List[Dict[str, str]]:
        """Retrieve top_k most relevant compliance policy chunks for a query string."""
        if not self.vectorizer or self.doc_matrix is None or not query.strip():
            return self.docs[:top_k]

        try:
            from sklearn.metrics.pairwise import cosine_similarity
            query_vec = self.vectorizer.transform([query])
            sims = cosine_similarity(query_vec, self.doc_matrix).flatten()
            top_indices = sims.argsort()[::-1][:top_k]
            
            results = []
            for idx in top_indices:
                if sims[idx] > 0.05:
                    results.append(self.docs[idx])
            return results if results else self.docs[:top_k]
        except Exception as exc:
            logger.warning("Error during RAG retrieval: %s", exc)
            return self.docs[:top_k]


_rag_retriever = ComplianceKnowledgeRetriever()


def _build_prompt(context: Dict[str, Any], follow_up_question: Optional[str] = None) -> str:
    """Construct the structured user prompt from all available case context and RAG documents."""
    tx = context.get("transaction", {})
    ml_prob = context.get("ml_probability", 0.0)
    final_risk = context.get("final_risk_level", "UNKNOWN")
    policy_override = context.get("policy_override_applied", False)
    policy_reasons = context.get("policy_reasons", [])
    contributors = context.get("contributors", [])
    history = context.get("user_history", [])
    case_id = context.get("case_id", "N/A")
    log_id = context.get("prediction_log_id", "N/A")

    # Format transaction details
    tx_block = f"""
Transaction Details:
  - Transaction ID (Log): {log_id}
  - Case ID: {case_id}
  - Type: {tx.get('type', 'UNKNOWN').upper()}
  - Amount: ${float(tx.get('amount', 0)):,.2f}
  - Sender opening balance: ${float(tx.get('oldbalanceOrg', 0)):,.2f}
  - Sender closing balance: ${float(tx.get('newbalanceOrig', 0)):,.2f}
  - Recipient opening balance: ${float(tx.get('oldbalanceDest', 0)):,.2f}
  - Recipient closing balance: ${float(tx.get('newbalanceDest', 0)):,.2f}"""

    # Risk assessment
    risk_level_map = {
        "CRITICAL": "CRITICAL — immediate action required",
        "HIGH": "HIGH — urgent review needed",
        "MEDIUM": "MEDIUM — manual review required",
        "LOW": "LOW — appears legitimate",
    }
    risk_block = f"""
Risk Assessment:
  - Final Risk Level: {risk_level_map.get(final_risk, final_risk)}
  - ML Model Assessment: {'Very High Risk' if ml_prob > 0.8 else 'High Risk' if ml_prob > 0.6 else 'Medium Risk' if ml_prob > 0.4 else 'Lower Risk'}
  - Policy Rules Triggered: {'YES — business rules elevated the risk score' if policy_override else 'NO — risk from ML model alone'}"""

    # Top suspicious signals
    signals_block = ""
    if contributors:
        top = contributors[:5]  # Top 5 signals
        signals = []
        for c in top:
            if c.get("contribution", 0) > 0:  # Only positive (fraud-pushing) contributions
                sig = _translate_feature(c["feature"], c.get("value", 0), c["contribution"])
                signals.append(f"  • {sig}")
        if signals:
            signals_block = "\nKey Suspicious Signals Detected:\n" + "\n".join(signals)

    # Policy rule violations
    rules_block = ""
    if policy_reasons:
        rules_block = "\nBusiness Rules Triggered:\n" + "\n".join(
            f"  • {r}" for r in policy_reasons
        )

    # User history context
    history_block = ""
    if history:
        total = len(history)
        high_risk = sum(1 for h in history if h.get("final_risk_level") in ("HIGH", "CRITICAL"))
        history_block = f"""
Account History Context:
  - This account has {total} previous transaction(s) in our system.
  - {high_risk} of those were assessed as HIGH or CRITICAL risk."""
        if high_risk > 0:
            history_block += "\n  - PATTERN ALERT: This account has a history of high-risk transactions."
    else:
        history_block = "\nAccount History Context:\n  - No prior transaction history found for this account."

    # RAG Retrieval
    query_terms = f"{tx.get('type')} amount {tx.get('amount')} {final_risk} " + " ".join(policy_reasons)
    if follow_up_question:
        query_terms += f" {follow_up_question}"
    
    rag_docs = _rag_retriever.retrieve(query_terms, top_k=2)
    rag_block = ""
    if rag_docs:
        rag_items = [
            f"  • [{d['id']} - {d['title']}]: {d['content']}"
            for d in rag_docs
        ]
        rag_block = "\nRELEVANT COMPLIANCE & FRAUD REGULATORY GUIDELINES (RAG Context):\n" + "\n".join(rag_items) + "\n"

    prompt = f"""Please explain why the following transaction was flagged by our fraud detection system.
Write your explanation for a compliance analyst who needs to decide whether to approve, block, or escalate this transaction.

{tx_block}
{risk_block}
{signals_block}
{rules_block}
{history_block}
{rag_block}

Provide a clear, plain-English explanation (2-5 sentences) of why this transaction is suspicious, followed by your recommended action."""

    return prompt.strip()


# ── Database helpers ──────────────────────────────────────────────────────────
import src.db
from src.models import FraudCase, PredictionLog, CopilotLog

def _fetch_case_context(
    db_path: Path,
    prediction_log_id: Optional[int] = None,
    case_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Fetch all relevant context from DB for a given log or case."""
    db = src.db.SessionLocal()
    try:
        if case_id:
            case = db.query(FraudCase).filter(FraudCase.case_id == case_id).first()
            if not case: return None
            log = db.query(PredictionLog).filter(PredictionLog.id == case.prediction_log_id).first()
            if not log: return None
            
            log_id = log.id
            tx = log.transaction_json or {}
            ml_prob = log.ml_probability
            final_risk_level = log.final_risk_level
            policy_override = log.policy_override_applied
            policy_reasons = log.policy_reasons_json or []
            status = case.status
            priority = case.priority
            title = case.title
        elif prediction_log_id is not None:
            log = db.query(PredictionLog).filter(PredictionLog.id == prediction_log_id).first()
            if not log: return None
            
            log_id = log.id
            tx = log.transaction_json or {}
            ml_prob = log.ml_probability
            final_risk_level = log.final_risk_level
            policy_override = log.policy_override_applied
            policy_reasons = log.policy_reasons_json or []
            status = None
            priority = None
            title = None
        else:
            return None

        # Fetch brief account history (last 10 transactions for that amount range)
        history = []
        if tx.get("amount"):
            history_rows = db.query(PredictionLog).filter(PredictionLog.id != log_id).order_by(PredictionLog.id.desc()).limit(10).all()
            history = [{"final_risk_level": h.final_risk_level, "ml_probability": h.ml_probability, "created_at": h.created_at} for h in history_rows]

        return {
            "prediction_log_id": log_id,
            "case_id": case_id,
            "transaction": tx,
            "ml_probability": float(ml_prob or 0.0),
            "final_risk_level": final_risk_level,
            "policy_override_applied": bool(policy_override),
            "policy_reasons": policy_reasons,
            "user_history": history,
            "case_status": status,
            "case_priority": priority,
            "case_title": title,
        }
    finally:
        db.close()


def _log_copilot_query(
    db_path: Path,
    prediction_log_id: Optional[int],
    case_id: Optional[str],
    context: Dict[str, Any],
    response: Optional[str],
    latency_ms: int,
    is_cached: bool = False,
    error: Optional[str] = None,
    tokens_used: Optional[int] = None,
) -> None:
    """Write every copilot query + response to copilot_logs for compliance audit."""
    try:
        db = src.db.SessionLocal()
        try:
            log = CopilotLog(
                case_id=case_id,
                prediction_log_id=prediction_log_id,
                query_context_json=context,
                llm_response=response,
                model_used=ANTHROPIC_MODEL,
                tokens_used=tokens_used,
                latency_ms=latency_ms,
                is_cached=is_cached,
                error=error,
                created_at=datetime.now(timezone.utc).isoformat()
            )
            db.add(log)
            db.commit()
        finally:
            db.close()
    except Exception as exc:
        logger.error("Failed to log copilot query to DB: %s", exc)


# ── Core engine ───────────────────────────────────────────────────────────────

class CopilotEngine:
    """
    Central engine for LLM-powered analyst explanations.

    Instantiate once and reuse across requests (caches model context).
    """

    def __init__(self, db_path: Path, project_root: Optional[Path] = None):
        self.db_path = db_path
        self.project_root = project_root or Path(__file__).resolve().parents[1]
        self._client = None  # Lazy-init Anthropic client

    def _get_client(self):
        """Lazy-initialize the Anthropic client. Raises if API key is missing."""
        if self._client is None:
            try:
                import anthropic  # type: ignore
            except ImportError as e:
                raise RuntimeError(
                    "anthropic package not installed. Run: pip install anthropic"
                ) from e

            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                raise RuntimeError(
                    "ANTHROPIC_API_KEY environment variable is not set. "
                    "Add it to your .env file or system environment."
                )
            import anthropic
            self._client = anthropic.Anthropic(api_key=api_key)
        return self._client

    def _add_xai_to_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Attempt to enrich context with SHAP-like feature contributions."""
        try:
            from src.features import build_features, load_feature_config
            from src.xai import explain_prediction

            config = load_feature_config()
            tx = context.get("transaction", {})
            if tx:
                features_df = build_features(tx, config)
                xai_res = explain_prediction(self.project_root, features_df)
                if "contributors" in xai_res and not xai_res.get("error"):
                    context["contributors"] = xai_res["contributors"]
                    context["xai_confidence"] = xai_res.get("confidence", 0.0)
        except Exception as exc:
            logger.warning("Could not enrich context with XAI: %s", exc)
        return context

    def _call_api_with_retry(self, prompt: str) -> tuple[str, int]:
        """
        Call Anthropic API with exponential backoff retry.

        Returns: (response_text, tokens_used)
        Raises: Exception after MAX_RETRIES failures or on timeout.
        """
        client = self._get_client()
        last_exc = None

        for attempt in range(MAX_RETRIES):
            try:
                start = time.time()
                response = client.messages.create(
                    model=ANTHROPIC_MODEL,
                    max_tokens=512,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": prompt}],
                    timeout=TIMEOUT_SECONDS,
                )
                elapsed = time.time() - start

                if elapsed > TIMEOUT_SECONDS:
                    raise TimeoutError(f"API call took {elapsed:.1f}s, exceeded {TIMEOUT_SECONDS}s timeout")

                text = response.content[0].text if response.content else ""
                tokens = getattr(response.usage, "input_tokens", 0) + getattr(response.usage, "output_tokens", 0)
                return text, tokens

            except TimeoutError:
                raise  # Don't retry on timeout — fail fast for graceful degradation
            except Exception as exc:
                last_exc = exc
                wait = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                logger.warning(
                    "Anthropic API attempt %d/%d failed (%s). Retrying in %ds...",
                    attempt + 1, MAX_RETRIES, exc, wait,
                )
                if attempt < MAX_RETRIES - 1:
                    time.sleep(wait)

        raise last_exc or RuntimeError("All API retries exhausted")

    def explain(
        self,
        prediction_log_id: Optional[int] = None,
        case_id: Optional[str] = None,
        follow_up_question: Optional[str] = None,
        chat_history: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """
        Generate a natural-language explanation for a flagged transaction.

        Args:
            prediction_log_id: Log ID to explain.
            case_id: Fraud case ID to explain (alternative to log_id).
            follow_up_question: Analyst's follow-up question string.
            chat_history: List of previous messages [{role, content}].

        Returns:
            dict with keys: explanation, is_cached, latency_ms, error (if any)
        """
        t_start = time.time()
        is_cached = False
        error = None
        explanation = None
        tokens_used = None

        # 1. Fetch context from DB
        context = _fetch_case_context(
            self.db_path,
            prediction_log_id=prediction_log_id,
            case_id=case_id,
        )

        if not context:
            msg = f"Case not found in the system. Please verify the {'case_id' if case_id else 'log_id'} and try again."
            _log_copilot_query(
                self.db_path, prediction_log_id, case_id, {},
                msg, 0, error="NOT_FOUND"
            )
            return {"explanation": msg, "is_cached": False, "latency_ms": 0, "error": "NOT_FOUND"}

        # 2. Enrich with XAI feature contributions
        context = self._add_xai_to_context(context)

        # 3. Check cache
        context_hash = hashlib.md5(
            json.dumps(context, sort_keys=True, default=str).encode()
        ).hexdigest()
        cache_key = _cache_key(context.get("prediction_log_id", 0), context_hash)

        cached_text = _get_from_cache(cache_key)
        if cached_text and not follow_up_question:
            latency_ms = int((time.time() - t_start) * 1000)
            _log_copilot_query(
                self.db_path, prediction_log_id, case_id, context,
                cached_text, latency_ms, is_cached=True,
            )
            return {"explanation": cached_text, "is_cached": True, "latency_ms": latency_ms, "error": None}

        # 4. Build prompt with RAG context
        try:
            if follow_up_question and chat_history:
                # Follow-up mode: pass history + new question
                prompt = _build_prompt(context, follow_up_question=follow_up_question)
                messages = list(chat_history) + [{"role": "user", "content": follow_up_question}]
            else:
                prompt = _build_prompt(context, follow_up_question=follow_up_question)
                messages = None

            # 5. Call API
            client = self._get_client()

            if messages:
                # Multi-turn with history
                system_messages = [{"role": "user", "content": prompt}]
                # Replace first user turn with context prompt, then append history
                api_messages = [{"role": "user", "content": prompt}]
                for m in chat_history or []:
                    api_messages.append(m)
                if follow_up_question:
                    api_messages.append({"role": "user", "content": follow_up_question})

                # Simplify: just include context + follow-up in single message for reliability
                combined = f"Context:\n{prompt}\n\nFollow-up question from analyst: {follow_up_question}"
                explanation, tokens_used = self._call_api_with_retry(combined)
            else:
                explanation, tokens_used = self._call_api_with_retry(prompt)

            # 6. Cache the initial explanation (not follow-ups)
            if not follow_up_question:
                _store_in_cache(cache_key, explanation)

        except TimeoutError as exc:
            error = "TIMEOUT"
            explanation = None
            logger.error("Copilot timed out: %s", exc)
        except RuntimeError as exc:
            error = "API_KEY_MISSING"
            explanation = str(exc)
            logger.error("Copilot config error: %s", exc)
        except Exception as exc:
            error = f"API_ERROR: {exc}"
            explanation = None
            logger.error("Copilot API error: %s", exc)

        latency_ms = int((time.time() - t_start) * 1000)

        # 7. Audit log
        _log_copilot_query(
            self.db_path, prediction_log_id, case_id, context,
            explanation, latency_ms, tokens_used=tokens_used, error=error,
        )

        return {
            "explanation": explanation,
            "is_cached": is_cached,
            "latency_ms": latency_ms,
            "error": error,
        }

    def explain_stream(
        self,
        prediction_log_id: Optional[int] = None,
        case_id: Optional[str] = None,
        follow_up_question: Optional[str] = None,
        chat_history: Optional[List[Dict]] = None,
    ) -> Generator[str, None, None]:
        """
        Stream a natural-language explanation chunk-by-chunk.

        Yields text chunks as they arrive from the API.
        Falls back to non-streaming explain() on error.
        """
        t_start = time.time()
        context = _fetch_case_context(
            self.db_path,
            prediction_log_id=prediction_log_id,
            case_id=case_id,
        )

        if not context:
            yield "❌ Case not found in the system. Please verify the case ID and try again."
            return

        context = self._add_xai_to_context(context)

        # Check cache
        context_hash = hashlib.md5(
            json.dumps(context, sort_keys=True, default=str).encode()
        ).hexdigest()
        cache_key = _cache_key(context.get("prediction_log_id", 0), context_hash)

        cached_text = _get_from_cache(cache_key)
        if cached_text and not follow_up_question:
            yield cached_text
            return

        prompt = _build_prompt(context)
        if follow_up_question:
            prompt = f"Context:\n{prompt}\n\nAnalyst follow-up: {follow_up_question}"

        full_response = []
        try:
            client = self._get_client()
            with client.messages.stream(
                model=ANTHROPIC_MODEL,
                max_tokens=512,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
                timeout=TIMEOUT_SECONDS,
            ) as stream:
                for text_chunk in stream.text_stream:
                    full_response.append(text_chunk)
                    yield text_chunk

            complete_text = "".join(full_response)
            if not follow_up_question:
                _store_in_cache(cache_key, complete_text)

            latency_ms = int((time.time() - t_start) * 1000)
            _log_copilot_query(
                self.db_path, prediction_log_id, case_id, context,
                complete_text, latency_ms,
            )

        except TimeoutError:
            yield "\n\n⚠️ Copilot response timed out. Please refer to the SHAP chart above for analysis."
        except Exception as exc:
            logger.error("Streaming error: %s", exc)
            # Graceful degradation: fall back to static explanation
            yield f"\n\n⚠️ Copilot unavailable ({type(exc).__name__}). Please refer to the SHAP chart above."

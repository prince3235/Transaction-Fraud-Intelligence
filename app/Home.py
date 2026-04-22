from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import html as html_lib
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime

from app.utils_dashboard  import get_db_path, load_logs_df, get_total_count
from app.premium_design   import inject_premium_design
from app.simulator        import build_transaction, batch_simulate, compute_ml_probability

# ════════════════════════════════════════════════════════════════════════════
#  PAGE CONFIG
# ════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Fraud Intelligence Platform",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_premium_design()

# ════════════════════════════════════════════════════════════════════════════
#  SESSION STATE  (persists across reruns)
# ════════════════════════════════════════════════════════════════════════════
if "sim_transactions" not in st.session_state:
    st.session_state.sim_transactions = []      # list[dict]
if "sim_counter"      not in st.session_state:
    st.session_state.sim_counter      = 9000    # auto-increment SIM ID
if "last_injected_id" not in st.session_state:
    st.session_state.last_injected_id = None    # highlight newest row


# ════════════════════════════════════════════════════════════════════════════
#  SIDEBAR  —  TRANSACTION SIMULATOR PANEL
# ════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div style="padding:1rem 0 0.5rem">
      <div style="font-size:10px;font-weight:700;color:#5A8AA8;
                  text-transform:uppercase;letter-spacing:0.14em;margin-bottom:6px;">
        ⚡ Simulation Engine
      </div>
      <div style="font-size:20px;font-weight:800;color:#E8F0FF;
                  letter-spacing:-0.03em;margin-bottom:4px;">
        Transaction Injector
      </div>
      <div style="font-size:12px;color:#3D5A72;margin-bottom:1.5rem;">
        Build &amp; inject transactions live
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # ── Manual transaction builder ──────────────────────────────────────────
    st.markdown('<p style="font-size:11px;font-weight:700;color:#5A8AA8;text-transform:uppercase;letter-spacing:0.12em;margin-bottom:12px;">Manual Builder</p>', unsafe_allow_html=True)

    amount = st.slider("Amount (₹)", min_value=100, max_value=100_000,
                       value=5_000, step=500, format="₹%d")

    merchant_type = st.selectbox("Merchant Type", [
        "POS Retail", "E-Commerce", "ATM Withdrawal",
        "Wire Transfer", "Crypto Exchange", "Gambling",
        "Utility Bill", "Travel Agency",
    ])

    country = st.selectbox("Country", [
        "India", "USA", "UK", "Germany", "UAE",
        "Brazil", "China", "Russia", "Nigeria", "Anonymous VPN",
    ])

    hour = st.slider("Transaction Hour (24h)", 0, 23, value=14)

    suspicious_signals = st.slider("Suspicious Signals", 0, 5, value=0,
                                   help="Number of risk flags triggered (velocity, pattern, etc.)")

    is_new_device = st.checkbox("🖥️  New Device", value=False)
    velocity_flag = st.checkbox("⚡  High Velocity", value=False)

    # ── Live Risk Score Preview ─────────────────────────────────────────────
    live_prob = compute_ml_probability(
        amount, merchant_type, country, hour,
        suspicious_signals, is_new_device, velocity_flag,
    )
    live_score = int(live_prob * 100)
    risk_color = {"CRITICAL":"#FF2D55","HIGH":"#FF8A00","MEDIUM":"#FFB800","LOW":"#00E5A0"}
    level_map  = lambda s: "CRITICAL" if s>=85 else "HIGH" if s>=60 else "MEDIUM" if s>=35 else "LOW"
    live_level = level_map(live_score)
    r_col      = risk_color[live_level]

    st.markdown(f"""
    <div style="background:rgba(8,13,26,0.9);border:1px solid {r_col}33;
                border-radius:12px;padding:14px 16px;margin:14px 0;">
      <div style="font-size:10px;font-weight:700;color:#5A8AA8;
                  text-transform:uppercase;letter-spacing:0.12em;margin-bottom:8px;">
        Live Risk Preview
      </div>
      <div style="display:flex;align-items:center;justify-content:space-between;">
        <div>
          <div style="font-size:32px;font-weight:800;color:{r_col};
                      letter-spacing:-0.04em;line-height:1;">{live_score}</div>
          <div style="font-size:10px;color:#3D5A72;margin-top:2px;">/ 100</div>
        </div>
        <div style="background:{r_col}18;border:1px solid {r_col}44;
                    color:{r_col};font-size:11px;font-weight:700;
                    letter-spacing:0.1em;text-transform:uppercase;
                    padding:6px 14px;border-radius:100px;">
          {live_level}
        </div>
      </div>
      <div style="margin-top:10px;height:4px;background:rgba(148,163,184,0.08);border-radius:100px;">
        <div style="height:100%;width:{live_score}%;background:{r_col};
                    border-radius:100px;transition:width 0.3s ease;"></div>
      </div>
      <div style="font-size:10px;color:#3D5A72;margin-top:6px;">
        ML Probability: {live_prob:.4f}
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Inject Button ───────────────────────────────────────────────────────
    if st.button("⚡  Inject Transaction", use_container_width=True, type="primary"):
        txn = build_transaction(
            amount, merchant_type, country, hour,
            suspicious_signals, is_new_device, velocity_flag,
            sim_id=st.session_state.sim_counter,
        )
        st.session_state.sim_transactions.insert(0, txn)
        st.session_state.last_injected_id = txn["id"]
        st.session_state.sim_counter += 1
        st.rerun()

    st.markdown("---")

    # ── Batch Simulator ─────────────────────────────────────────────────────
    st.markdown('<p style="font-size:11px;font-weight:700;color:#5A8AA8;text-transform:uppercase;letter-spacing:0.12em;margin-bottom:12px;">Batch Simulator</p>', unsafe_allow_html=True)

    batch_n         = st.slider("Transactions to generate", 5, 100, value=20, step=5)
    fraud_ratio     = st.slider("Fraud mix %", 0, 100, value=40, step=5,
                                help="% of generated transactions that are high-risk") / 100

    if st.button(f"🎲  Simulate {batch_n} Transactions", use_container_width=True):
        new_txns = batch_simulate(
            n=batch_n,
            start_id=st.session_state.sim_counter,
            high_risk_ratio=fraud_ratio,
        )
        st.session_state.sim_transactions = new_txns + st.session_state.sim_transactions
        st.session_state.last_injected_id = new_txns[0]["id"]
        st.session_state.sim_counter += batch_n
        st.rerun()

    # ── Stats + Clear ───────────────────────────────────────────────────────
    sim_count = len(st.session_state.sim_transactions)
    if sim_count:
        sim_df     = pd.DataFrame(st.session_state.sim_transactions)
        sim_high   = int((sim_df["final_risk_level"].isin(["HIGH","CRITICAL"])).sum())
        sim_crit   = int((sim_df["final_risk_level"] == "CRITICAL").sum())

        st.markdown(f"""
        <div style="background:rgba(0,180,255,0.06);border:1px solid rgba(0,180,255,0.15);
                    border-radius:10px;padding:12px 14px;margin:12px 0;">
          <div style="font-size:10px;font-weight:700;color:#5A8AA8;
                      text-transform:uppercase;letter-spacing:0.12em;margin-bottom:8px;">
            Session Stats
          </div>
          <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
            <span style="font-size:12px;color:#5A8AA8;">Injected</span>
            <span style="font-size:13px;font-weight:700;color:#E8F0FF;">{sim_count}</span>
          </div>
          <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
            <span style="font-size:12px;color:#5A8AA8;">High Risk</span>
            <span style="font-size:13px;font-weight:700;color:#FF8A00;">{sim_high}</span>
          </div>
          <div style="display:flex;justify-content:space-between;">
            <span style="font-size:12px;color:#5A8AA8;">Critical</span>
            <span style="font-size:13px;font-weight:700;color:#FF2D55;">{sim_crit}</span>
          </div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("🗑️  Clear Simulated Data", use_container_width=True):
            st.session_state.sim_transactions = []
            st.session_state.last_injected_id = None
            st.rerun()

    st.markdown("""
    <div style="font-size:10px;color:#1E3247;text-align:center;
                padding-top:1rem;letter-spacing:0.05em;">
      Simulation Engine v1.0 · Session only
    </div>
    """, unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
#  LOAD DATA + MERGE SIMULATED TRANSACTIONS
# ════════════════════════════════════════════════════════════════════════════
DB_PATH     = get_db_path(PROJECT_ROOT)
total_count = get_total_count(DB_PATH)
df_db       = load_logs_df(DB_PATH, limit=10000)

# Merge simulated transactions into the dataframe
if st.session_state.sim_transactions:
    sim_df = pd.DataFrame(st.session_state.sim_transactions)
    # Ensure created_at is datetime
    sim_df["created_at"] = pd.to_datetime(sim_df["created_at"])
    # Fill missing columns that may not be in simulator output
    for col in df_db.columns:
        if col not in sim_df.columns:
            sim_df[col] = None
    df_all = pd.concat([sim_df[df_db.columns.tolist() + ["_is_simulated"]
                                if "_is_simulated" in sim_df.columns else df_db.columns.tolist()],
                        df_db], ignore_index=True)
    # Keep _is_simulated flag
    if "_is_simulated" not in df_all.columns:
        df_all["_is_simulated"] = False
    df_all["_is_simulated"] = df_all["_is_simulated"].fillna(False)
else:
    df_all = df_db.copy()
    df_all["_is_simulated"] = False

df = df_all.copy()

# Effective total (DB + simulated)
effective_total = total_count + len(st.session_state.sim_transactions)


# ════════════════════════════════════════════════════════════════════════════
#  HEADER
# ════════════════════════════════════════════════════════════════════════════
sim_count = len(st.session_state.sim_transactions)
sim_badge = (
    f'<span style="background:rgba(0,229,160,0.12);border:1px solid rgba(0,229,160,0.3);'
    f'color:#00E5A0;font-size:11px;font-weight:700;padding:3px 12px;border-radius:100px;'
    f'margin-left:12px;">+{sim_count} SIMULATED</span>'
    if sim_count else ""
)

col_title, col_btn = st.columns([5, 1])
with col_title:
    st.markdown(f"""
    <div style="padding:0.5rem 0 1.5rem">
      <div class="live-badge">
        <span class="live-dot"></span>
        Live Monitoring
      </div>
      <div class="page-title">
        Fraud Intelligence
        <span class="gradient-word">Platform</span>
        {sim_badge}
      </div>
      <div class="page-subtitle">
        Real-time Transaction Monitoring &amp; Risk Intelligence System
      </div>
    </div>
    """, unsafe_allow_html=True)

with col_btn:
    st.markdown('<div style="height:80px"></div>', unsafe_allow_html=True)
    if st.button("↻  Refresh", use_container_width=True):
        st.rerun()

st.markdown('<div class="hdivider"></div>', unsafe_allow_html=True)

if df.empty:
    st.info("⚠️  No transaction logs found.")
    st.stop()


# ════════════════════════════════════════════════════════════════════════════
#  KPI METRICS  (include simulated in live count)
# ════════════════════════════════════════════════════════════════════════════
critical      = int((df["final_risk_level"] == "CRITICAL").sum())
high          = int((df["final_risk_level"] == "HIGH").sum())
override_rate = float(df["policy_override_applied"].mean() * 100)
avg_score     = float(df["final_risk_score"].mean())

m1, m2, m3, m4, m5 = st.columns(5)
CARD_DEFS = [
    (m1, "Total Transactions", f"{effective_total:,}",   "DB + simulated",                                                "blue"),
    (m2, "Critical Alerts",    f"{critical:,}",           f"{critical/effective_total*100:.2f}% of total",                 "red"),
    (m3, "High Risk",          f"{high:,}",               f"{high/effective_total*100:.2f}% of total",                     "orange"),
    (m4, "Override Rate",      f"{override_rate:.1f}%",   f"{int(df['policy_override_applied'].sum()):,} triggers",         "purple"),
    (m5, "Avg Risk Score",     f"{avg_score:.0f}",        "out of 100",                                                    "teal"),
]

for col, label, value, sub, accent in CARD_DEFS:
    with col:
        st.markdown(f"""
        <div class="kpi-card kpi-{accent}">
          <div class="kpi-stripe"></div>
          <div class="kpi-glow-blob"></div>
          <div class="kpi-label">{label}</div>
          <div class="kpi-value">{value}</div>
          <div class="kpi-sub">{sub}</div>
        </div>
        """, unsafe_allow_html=True)

# ── Live injection notification ──────────────────────────────────────────────
if st.session_state.last_injected_id and sim_count > 0:
    last = next(
        (t for t in st.session_state.sim_transactions
         if t["id"] == st.session_state.last_injected_id), None
    )
    if last:
        lvl   = last["final_risk_level"]
        score = last["final_risk_score"]
        r_col = {"CRITICAL":"#FF2D55","HIGH":"#FF8A00","MEDIUM":"#FFB800","LOW":"#00E5A0"}.get(lvl,"#8899AA")
        st.markdown(f"""
        <div style="background:rgba(0,229,160,0.06);border:1px solid rgba(0,229,160,0.2);
                    border-left:3px solid #00E5A0;border-radius:10px;
                    padding:10px 16px;margin:1rem 0;
                    display:flex;align-items:center;gap:14px;">
          <span style="font-size:16px;">⚡</span>
          <div>
            <span style="font-size:12px;font-weight:700;color:#00E5A0;">
              Transaction {last['id']} injected
            </span>
            <span style="font-size:12px;color:#3D5A72;margin-left:10px;">
              {last.get('merchant_type','—')} · {last.get('country','—')} ·
              ₹{last.get('amount',0):,.0f}
            </span>
          </div>
          <div style="margin-left:auto;background:{r_col}18;border:1px solid {r_col}44;
                      color:{r_col};font-size:10px;font-weight:700;letter-spacing:0.1em;
                      text-transform:uppercase;padding:4px 12px;border-radius:100px;">
            {lvl} · {score}
          </div>
        </div>
        """, unsafe_allow_html=True)

st.markdown('<div class="section-gap"></div>', unsafe_allow_html=True)
st.markdown('<div class="hdivider"></div>', unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
#  CHARTS
# ════════════════════════════════════════════════════════════════════════════
chart_left, chart_right = st.columns(2)

# ── DONUT (always unfiltered full picture) ────────────────────────────────
with chart_left:
    st.markdown('<div class="chart-card"><div class="chart-card-title">Risk Distribution</div>', unsafe_allow_html=True)

    dist_all   = df["final_risk_level"].value_counts()
    C_MAP      = {"LOW":"#00E5A0","MEDIUM":"#FFB800","HIGH":"#FF8A00","CRITICAL":"#FF2D55"}
    ALL_LEVELS = ["LOW","MEDIUM","HIGH","CRITICAL"]
    d_values   = [int(dist_all.get(l, 0)) for l in ALL_LEVELS]
    d_colors   = [C_MAP[l] for l in ALL_LEVELS]
    donut_total = sum(d_values)

    fig_donut = go.Figure(go.Pie(
        labels=ALL_LEVELS, values=d_values, hole=0.70,
        marker=dict(colors=d_colors, line=dict(color="#05080F", width=5)),
        textinfo="none", sort=False,
        customdata=[f"{v/donut_total*100:.1f}%" if donut_total else "0%" for v in d_values],
        hovertemplate="<b>%{label}</b><br>%{value:,} transactions<br>%{customdata}<extra></extra>",
    ))
    fig_donut.update_layout(
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.18,
                    xanchor="center", x=0.5,
                    font=dict(size=12, color="#4B6180", family="DM Sans"),
                    itemsizing="constant"),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=10, b=100), height=380,
        annotations=[dict(
            text=(
                f'<span style="font-size:34px;font-weight:800;'
                f'font-family:DM Sans;color:#F0F4FF;">{donut_total:,}</span>'
                f'<br>'
                f'<span style="font-size:10px;font-weight:700;'
                f'letter-spacing:0.14em;color:#2E4A60;">TOTAL</span>'
            ),
            x=0.5, y=0.5, showarrow=False, align="center",
            font=dict(family="DM Sans", color="#F0F4FF"),
        )],
    )
    st.plotly_chart(fig_donut, use_container_width=True, config={"displayModeBar": False})
    st.markdown("""
    <div style="font-size:10px;color:#1E3247;text-align:center;
                letter-spacing:0.08em;padding:0 0 8px;margin-top:-6px;">
      FULL DATASET · INCLUDES SIMULATED
    </div>""", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ── LINE CHART ────────────────────────────────────────────────────────────
with chart_right:
    st.markdown('<div class="chart-card"><div class="chart-card-title">Alert Trend — Last 14 Days</div>', unsafe_allow_html=True)

    tmp = df.dropna(subset=["created_at"]).copy()
    tmp = tmp[tmp["final_risk_level"].isin(["HIGH","CRITICAL"])]

    if tmp.empty:
        st.info("No high-risk alerts found.")
    else:
        tmp["date"] = pd.to_datetime(tmp["created_at"]).dt.floor("D")
        alerts      = tmp.groupby("date").size().reset_index(name="count").tail(14)

        # Separate simulated points for overlay
        tmp_sim = tmp[tmp.get("_is_simulated", pd.Series(False, index=tmp.index)) == True] if "_is_simulated" in tmp.columns else pd.DataFrame()

        fig_line = go.Figure()
        fig_line.add_trace(go.Scatter(
            x=alerts["date"], y=alerts["count"],
            mode="none", fill="tozeroy",
            fillcolor="rgba(0,180,255,0.07)",
            showlegend=False, hoverinfo="skip",
        ))
        fig_line.add_trace(go.Scatter(
            x=alerts["date"], y=alerts["count"],
            mode="lines+markers",
            line=dict(color="#00B4FF", width=2.5, shape="spline", smoothing=1.2),
            marker=dict(color="#05080F", size=8, line=dict(color="#00B4FF", width=2.5)),
            hovertemplate="<b>%{x|%b %d}</b>  —  %{y:,} alerts<extra></extra>",
            showlegend=False,
        ))

        # Highlight today's simulated point if any
        if not tmp_sim.empty and sim_count:
            today_sim = tmp_sim.copy()
            today_sim["date"] = today_sim["created_at"].dt.floor("D")
            today_counts = today_sim.groupby("date").size().reset_index(name="count")
            fig_line.add_trace(go.Scatter(
                x=today_counts["date"], y=today_counts["count"],
                mode="markers",
                marker=dict(color="#00E5A0", size=12,
                            line=dict(color="#05080F", width=2),
                            symbol="star"),
                name="Simulated",
                hovertemplate="<b>SIMULATED</b> %{x|%b %d} — %{y:,}<extra></extra>",
            ))

        fig_line.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=10, r=10, t=10, b=10), height=380,
            xaxis=dict(showgrid=False, showline=False, tickformat="%b %d",
                       color="#2E4258", tickfont=dict(size=11, family="DM Sans")),
            yaxis=dict(showgrid=True, gridcolor="rgba(148,163,184,0.05)",
                       zeroline=False, showline=False,
                       color="#2E4258", tickfont=dict(size=11, family="DM Sans"),
                       tickformat="d"),
            font=dict(family="DM Sans", color="#8899AA"),
            hovermode="x unified",
            hoverlabel=dict(bgcolor="#0A1020", bordercolor="rgba(0,180,255,0.3)",
                            font=dict(family="DM Sans", size=13, color="#F0F4FF"), namelength=0),
            showlegend=sim_count > 0,
            legend=dict(font=dict(size=11, color="#5A8AA8", family="DM Sans"),
                        bgcolor="rgba(0,0,0,0)", bordercolor="rgba(0,0,0,0)"),
        )
        st.plotly_chart(fig_line, use_container_width=True, config={"displayModeBar": False})

    st.markdown("</div>", unsafe_allow_html=True)

st.markdown('<div class="hdivider" style="margin:2.5rem 0"></div>', unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
#  LIVE FEED  (only shown when simulated transactions exist)
# ════════════════════════════════════════════════════════════════════════════
if st.session_state.sim_transactions:
    st.markdown("""
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:1.25rem;">
      <div style="font-size:11px;font-weight:700;color:#5A8AA8;
                  text-transform:uppercase;letter-spacing:0.14em;">Live Feed</div>
      <div style="display:inline-flex;align-items:center;gap:6px;
                  background:rgba(0,229,160,0.10);border:1px solid rgba(0,229,160,0.25);
                  color:#00E5A0;font-size:10px;font-weight:700;letter-spacing:0.12em;
                  text-transform:uppercase;padding:3px 10px;border-radius:100px;">
        <span style="width:5px;height:5px;border-radius:50%;background:#00E5A0;
                     display:inline-block;"></span>
        SIMULATED
      </div>
    </div>
    """, unsafe_allow_html=True)

    RISK_STYLE = {
        "LOW":      ("#00E5A0","rgba(0,229,160,0.10)"),
        "MEDIUM":   ("#FFB800","rgba(255,184,0,0.10)"),
        "HIGH":     ("#FF8A00","rgba(255,138,0,0.10)"),
        "CRITICAL": ("#FF2D55","rgba(255,45,85,0.10)"),
    }

    def rbadge_live(level):
        fg, bg = RISK_STYLE.get(str(level).upper(), ("#8899AA","rgba(136,153,170,0.1)"))
        return (f'<span style="background:{bg};color:{fg};border:1px solid {fg}40;'
                f'font-size:10px;font-weight:700;letter-spacing:0.1em;'
                f'text-transform:uppercase;padding:3px 10px;border-radius:100px;">'
                f'{level}</span>')

    FEED_HEADS = ["ID","Time","Amount","Merchant","Country","ML Prob","Final Risk","Score","Override"]
    th_live = "".join(
        f'<th style="padding:9px 12px;font-size:10px;font-weight:700;color:#5A8AA8;'
        f'text-transform:uppercase;letter-spacing:0.12em;text-align:left;'
        f'border-bottom:1px solid rgba(148,163,184,0.07);white-space:nowrap;">{h}</th>'
        for h in FEED_HEADS
    )

    feed_rows = ""
    for txn in st.session_state.sim_transactions[:20]:
        is_last = txn["id"] == st.session_state.last_injected_id
        row_bg  = "rgba(0,229,160,0.04)" if is_last else "transparent"
        ov      = ('<span style="color:#A855F7;font-weight:700;">✓</span>'
                   if txn.get("policy_override_applied") else
                   '<span style="color:#1A2535;">—</span>')
        ts = txn["created_at"].strftime("%H:%M:%S") if isinstance(txn["created_at"], datetime) else str(txn["created_at"])[-8:]
        TD = f'style="padding:9px 12px;border-bottom:1px solid rgba(148,163,184,0.04);background:{row_bg};"'
        feed_rows += (
            f'<tr>'
            f'<td {TD}><span style="font-family:DM Mono,monospace;font-size:11px;color:#5A8AA8;">{txn["id"]}</span>'
            f'{"<span style=margin-left:6px;font-size:9px;background:rgba(0,229,160,0.12);color:#00E5A0;border-radius:4px;padding:1px 5px;>NEW</span>" if is_last else ""}</td>'
            f'<td {TD}><span style="font-size:11px;color:#4B6180;font-family:DM Mono,monospace;">{ts}</span></td>'
            f'<td {TD}><span style="font-size:12px;font-weight:600;color:#8899AA;">₹{txn.get("amount",0):,.0f}</span></td>'
            f'<td {TD}><span style="font-size:11px;color:#5A8AA8;">{txn.get("merchant_type","—")}</span></td>'
            f'<td {TD}><span style="font-size:11px;color:#5A8AA8;">{txn.get("country","—")}</span></td>'
            f'<td {TD}><span style="font-family:DM Mono,monospace;font-size:11px;color:#4B6180;">{txn["ml_probability"]:.4f}</span></td>'
            f'<td {TD}>{rbadge_live(txn["final_risk_level"])}</td>'
            f'<td {TD}><span style="font-family:DM Mono,monospace;font-size:13px;font-weight:700;color:#C4CFDE;">{txn["final_risk_score"]}</span></td>'
            f'<td {TD} style="text-align:center;padding:9px 12px;border-bottom:1px solid rgba(148,163,184,0.04);background:{row_bg};">{ov}</td>'
            f'</tr>'
        )

    st.markdown(
        '<div style="background:rgba(6,9,18,0.92);border:1px solid rgba(0,229,160,0.12);'
        'border-radius:16px;overflow:hidden;overflow-x:auto;">'
        f'<table style="width:100%;border-collapse:collapse;min-width:800px;">'
        f'<thead><tr style="background:rgba(0,229,160,0.04);">{th_live}</tr></thead>'
        f'<tbody>{feed_rows}</tbody>'
        '</table></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="hdivider" style="margin:2.5rem 0"></div>', unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
#  POLICY OVERRIDE ANALYSIS
# ════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-label">Policy Override Analysis</div>', unsafe_allow_html=True)

override_df = df[df["policy_override_applied"] == 1]

if not override_df.empty:
    oc1, oc2 = st.columns([1, 3])

    with oc1:
        st.markdown(f"""
        <div class="kpi-card kpi-purple" style="min-height:auto;padding:22px 20px 18px;">
          <div class="kpi-stripe"></div>
          <div class="kpi-glow-blob"></div>
          <div class="kpi-label">Total Overrides</div>
          <div class="kpi-value">{len(override_df):,}</div>
          <div class="kpi-sub">{len(override_df)/len(df)*100:.1f}% of all transactions</div>
        </div>
        """, unsafe_allow_html=True)

    with oc2:
        all_reasons = []
        for r in override_df["policy_reasons"]:
            if isinstance(r, list):
                all_reasons.extend(r)

        if all_reasons:
            top   = pd.Series(all_reasons).value_counts().head(5)
            max_c = top.iloc[0]
            rows  = ""
            for reason, count in top.items():
                pct      = count / len(override_df) * 100
                bar_w    = count / max_c * 100
                safe_rsn = html_lib.escape(str(reason))
                rows += (
                    '<div style="display:flex;align-items:center;gap:14px;padding:10px 0;'
                    'border-bottom:1px solid rgba(148,163,184,0.05);">'
                        f'<div style="font-size:12px;font-weight:500;color:#7A9DB8;'
                        f'min-width:220px;white-space:nowrap;overflow:hidden;'
                        f'text-overflow:ellipsis;">{safe_rsn}</div>'
                        '<div style="flex:1;height:5px;background:rgba(148,163,184,0.07);'
                        'border-radius:100px;overflow:hidden;">'
                            f'<div style="height:100%;width:{bar_w:.1f}%;'
                            'background:linear-gradient(90deg,#00B4FF,#A855F7);'
                            'border-radius:100px;"></div>'
                        '</div>'
                        '<div style="min-width:90px;display:flex;align-items:center;'
                        'gap:8px;justify-content:flex-end;">'
                            f'<span style="font-size:12px;font-weight:700;color:#8899AA;">{count:,}</span>'
                            f'<span style="font-size:11px;color:#5A8AA8;">{pct:.1f}%</span>'
                        '</div>'
                    '</div>'
                )
            st.markdown(
                '<div style="background:rgba(8,13,26,0.88);border:1px solid rgba(148,163,184,0.09);'
                'border-radius:16px;padding:20px 24px 12px;">'
                '<div style="font-size:10px;font-weight:700;color:#5A8AA8;text-transform:uppercase;'
                'letter-spacing:0.13em;margin-bottom:14px;">Top Triggers</div>'
                + rows + '</div>',
                unsafe_allow_html=True,
            )
else:
    st.info("No policy overrides detected.")

st.markdown('<div class="hdivider" style="margin:2.5rem 0"></div>', unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
#  RECENT TRANSACTIONS TABLE  (DB data, latest 40)
# ════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-label">Recent Transactions (Database)</div>', unsafe_allow_html=True)

table_df = df_db[[
    "id","created_at","ml_probability","ml_risk_level",
    "final_risk_level","final_risk_score","policy_override_applied"
]].head(40).copy()
table_df["created_at"]     = table_df["created_at"].dt.strftime("%Y-%m-%d %H:%M")
table_df["ml_probability"] = table_df["ml_probability"].round(4)

RISK_STYLE = {
    "LOW":      ("#00E5A0","rgba(0,229,160,0.10)"),
    "MEDIUM":   ("#FFB800","rgba(255,184,0,0.10)"),
    "HIGH":     ("#FF8A00","rgba(255,138,0,0.10)"),
    "CRITICAL": ("#FF2D55","rgba(255,45,85,0.10)"),
}

def rbadge(level):
    fg, bg = RISK_STYLE.get(str(level).upper(), ("#8899AA","rgba(136,153,170,0.1)"))
    return (f'<span style="background:{bg};color:{fg};border:1px solid {fg}40;'
            f'font-size:10px;font-weight:700;letter-spacing:0.1em;'
            f'text-transform:uppercase;padding:3px 10px;border-radius:100px;">'
            f'{level}</span>')

HEADS = ["ID","Timestamp","ML Prob","ML Risk","Final Risk","Score","Override"]
th = "".join(
    f'<th style="padding:10px 14px;font-size:10px;font-weight:700;color:#5A8AA8;'
    f'text-transform:uppercase;letter-spacing:0.12em;text-align:left;'
    f'border-bottom:1px solid rgba(148,163,184,0.07);white-space:nowrap;">{h}</th>'
    for h in HEADS
)

tbody = ""
for _, row in table_df.iterrows():
    ov  = ('<span style="color:#A855F7;font-weight:700;">✓</span>'
           if row["policy_override_applied"] else
           '<span style="color:#1A2535;">—</span>')
    TD  = 'style="padding:10px 14px;border-bottom:1px solid rgba(148,163,184,0.04);"'
    tbody += (
        f'<tr>'
        f'<td {TD}><span style="font-family:DM Mono,monospace;font-size:12px;color:#5A8AA8;">{int(row["id"])}</span></td>'
        f'<td {TD}><span style="font-size:12px;color:#6B9AB8;white-space:nowrap;">{row["created_at"]}</span></td>'
        f'<td {TD}><span style="font-family:DM Mono,monospace;font-size:12px;color:#5A8AA8;">{row["ml_probability"]:.4f}</span></td>'
        f'<td {TD}>{rbadge(row["ml_risk_level"])}</td>'
        f'<td {TD}>{rbadge(row["final_risk_level"])}</td>'
        f'<td {TD}><span style="font-family:DM Mono,monospace;font-size:13px;font-weight:700;color:#C4CFDE;">{int(row["final_risk_score"])}</span></td>'
        f'<td {TD} style="padding:10px 14px;border-bottom:1px solid rgba(148,163,184,0.04);text-align:center;">{ov}</td>'
        f'</tr>'
    )

st.markdown(
    '<div style="background:rgba(6,9,18,0.92);border:1px solid rgba(148,163,184,0.09);'
    'border-radius:16px;overflow:hidden;overflow-x:auto;">'
    f'<table style="width:100%;border-collapse:collapse;min-width:700px;">'
    f'<thead><tr style="background:rgba(3,5,12,0.7);">{th}</tr></thead>'
    f'<tbody>{tbody}</tbody>'
    '</table></div>',
    unsafe_allow_html=True,
)

# ════════════════════════════════════════════════════════════════════════════
#  FOOTER
# ════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div style="text-align:center;font-size:12px;color:#1A2535;letter-spacing:0.06em;
            padding:2.5rem 0 1.5rem;display:flex;align-items:center;
            justify-content:center;gap:10px;">
  <span style="width:3px;height:3px;border-radius:50%;background:#1A2535;display:inline-block;"></span>
  Fraud Intelligence Platform &nbsp;·&nbsp; ML + Python + Streamlit
  &nbsp;·&nbsp; Simulation Engine v1.0
  <span style="width:3px;height:3px;border-radius:50%;background:#1A2535;display:inline-block;"></span>
</div>
""", unsafe_allow_html=True)
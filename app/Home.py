from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import html as html_lib

from app.utils_dashboard import get_db_path, load_logs_df, get_total_count
from app.premium_design import inject_premium_design

# ── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Fraud Intelligence Platform",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_premium_design()

# ── LOAD DATA ────────────────────────────────────────────────────────────────
DB_PATH     = get_db_path(PROJECT_ROOT)
total_count = get_total_count(DB_PATH)

# df_all — NEVER filtered, used for true distribution in donut
df_all = load_logs_df(DB_PATH, limit=10000)

# df — may be filtered downstream by risk level / score / override filters
df     = df_all.copy()

# ── HEADER ───────────────────────────────────────────────────────────────────
col_title, col_btn = st.columns([5, 1])
with col_title:
    st.markdown("""
    <div style="padding:0.5rem 0 1.5rem">
      <div class="live-badge">
        <span class="live-dot"></span>
        Live Monitoring
      </div>
      <div class="page-title">
        Fraud Intelligence
        <span class="gradient-word">Platform</span>
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

# ── DATA CHECK ───────────────────────────────────────────────────────────────
if df.empty:
    st.info("⚠️  No transaction logs found.")
    st.stop()

# ── METRICS ──────────────────────────────────────────────────────────────────
critical      = int((df["final_risk_level"] == "CRITICAL").sum())
high          = int((df["final_risk_level"] == "HIGH").sum())
override_rate = float(df["policy_override_applied"].mean() * 100)
avg_score     = float(df["final_risk_score"].mean())

# ── KPI CARDS ────────────────────────────────────────────────────────────────
m1, m2, m3, m4, m5 = st.columns(5)

CARD_DEFS = [
    (m1, "Total Transactions", f"{total_count:,}",      "All time records",                                              "blue"),
    (m2, "Critical Alerts",    f"{critical:,}",          f"{critical/total_count*100:.2f}% of total" if total_count else "–", "red"),
    (m3, "High Risk",          f"{high:,}",              f"{high/total_count*100:.2f}% of total"     if total_count else "–", "orange"),
    (m4, "Override Rate",      f"{override_rate:.1f}%",  f"{int(df['policy_override_applied'].sum()):,} triggers",        "purple"),
    (m5, "Avg Risk Score",     f"{avg_score:.0f}",       "out of 100",                                                    "teal"),
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

st.markdown('<div class="section-gap"></div>', unsafe_allow_html=True)
st.markdown('<div class="hdivider"></div>', unsafe_allow_html=True)

# ── CHARTS ───────────────────────────────────────────────────────────────────
chart_left, chart_right = st.columns(2)

# ─── DONUT ──────────────────────────────────────────────────────────────────
with chart_left:
    st.markdown('<div class="chart-card"><div class="chart-card-title">Risk Distribution</div>', unsafe_allow_html=True)

    # ⚠️  ALWAYS use df_all (unfiltered) so all 4 segments are visible
    #     even when user has filters applied on the page
    dist_all = df_all["final_risk_level"].value_counts()

    C_MAP    = {"LOW":"#00E5A0","MEDIUM":"#FFB800","HIGH":"#FF8A00","CRITICAL":"#FF2D55"}
    # Force all 4 categories — fill 0 if a level has no data
    ALL_LEVELS = ["LOW","MEDIUM","HIGH","CRITICAL"]
    d_labels   = ALL_LEVELS
    d_values   = [int(dist_all.get(l, 0)) for l in ALL_LEVELS]
    d_colors   = [C_MAP[l] for l in ALL_LEVELS]

    # Total from unfiltered df
    donut_total = int(df_all["final_risk_level"].notna().sum())

    fig_donut = go.Figure(go.Pie(
        labels=d_labels, values=d_values, hole=0.70,
        marker=dict(colors=d_colors, line=dict(color="#05080F", width=5)),
        textinfo="none", sort=False,
        customdata=[f"{v/donut_total*100:.1f}%" if donut_total else "0%" for v in d_values],
        hovertemplate="<b>%{label}</b><br>%{value:,} transactions<br>%{customdata}<extra></extra>",
    ))
    fig_donut.update_layout(
        showlegend=True,
        legend=dict(
            orientation="h", yanchor="bottom", y=-0.18,
            xanchor="center", x=0.5,
            font=dict(size=12, color="#4B6180", family="DM Sans"),
            itemsizing="constant",
        ),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=10, b=100), height=380,
        annotations=[dict(
            text=f"<b>{donut_total:,}</b><br>TOTAL",
            x=0.5, y=0.5, showarrow=False, align="center",
            font=dict(family="DM Sans", size=30, color="#F0F4FF"),
        )],
    )
    st.plotly_chart(fig_donut, use_container_width=True, config={"displayModeBar": False})

    # Caption — tells user this is always the full picture
    st.markdown("""
    <div style="font-size:10px;color:#1E3247;text-align:center;
                letter-spacing:0.08em;padding:0 0 8px;margin-top:-6px;">
      FULL DATASET · UNAFFECTED BY FILTERS
    </div>""", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ─── LINE CHART ──────────────────────────────────────────────────────────────
with chart_right:
    st.markdown('<div class="chart-card"><div class="chart-card-title">Alert Trend — Last 14 Days</div>', unsafe_allow_html=True)

    tmp = df.dropna(subset=["created_at"]).copy()
    tmp = tmp[tmp["final_risk_level"].isin(["HIGH","CRITICAL"])]

    if tmp.empty:
        st.info("No high-risk alerts found.")
    else:
        tmp["date"] = tmp["created_at"].dt.floor("D")
        alerts = tmp.groupby("date").size().reset_index(name="count").tail(14)

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
        fig_line.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=10, r=10, t=10, b=10), height=380,
            xaxis=dict(showgrid=False, showline=False, tickformat="%b %d",
                       color="#2E4258", tickfont=dict(size=11, family="DM Sans")),
            yaxis=dict(showgrid=True, gridcolor="rgba(148,163,184,0.05)",
                       zeroline=False, showline=False,
                       color="#2E4258", tickfont=dict(size=11, family="DM Sans")),
            font=dict(family="DM Sans", color="#8899AA"),
            hovermode="x unified",
            hoverlabel=dict(bgcolor="#0A1020", bordercolor="rgba(0,180,255,0.3)",
                            font=dict(family="DM Sans", size=13, color="#F0F4FF"), namelength=0),
        )
        st.plotly_chart(fig_line, use_container_width=True, config={"displayModeBar": False})

    st.markdown("</div>", unsafe_allow_html=True)

st.markdown('<div class="hdivider" style="margin:2.5rem 0"></div>', unsafe_allow_html=True)

# ── OVERRIDE ANALYSIS ────────────────────────────────────────────────────────
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
                            f'<span style="font-size:12px;font-weight:700;color:#8899AA;'
                            f'font-variant-numeric:tabular-nums;">{count:,}</span>'
                            f'<span style="font-size:11px;color:#5A8AA8;">{pct:.1f}%</span>'
                        '</div>'
                    '</div>'
                )

            st.markdown(
                '<div style="background:rgba(8,13,26,0.88);border:1px solid rgba(148,163,184,0.09);'
                'border-radius:16px;padding:20px 24px 12px;">'
                '<div style="font-size:10px;font-weight:700;color:#5A8AA8;text-transform:uppercase;'
                'letter-spacing:0.13em;margin-bottom:14px;">Top Triggers</div>'
                + rows +
                '</div>',
                unsafe_allow_html=True
            )
else:
    st.info("No policy overrides detected.")

st.markdown('<div class="hdivider" style="margin:2.5rem 0"></div>', unsafe_allow_html=True)

# ── RECENT TRANSACTIONS (Custom HTML Table — avoids Streamlit iframe) ────────
st.markdown('<div class="section-label">Recent Transactions</div>', unsafe_allow_html=True)

table_df = df[[
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
    ov = ('<span style="color:#A855F7;font-size:13px;font-weight:700;">✓</span>'
          if row["policy_override_applied"] else
          '<span style="color:#1A2535;">—</span>')
    TD = 'style="padding:10px 14px;border-bottom:1px solid rgba(148,163,184,0.04);"'
    tbody += f"""<tr>
      <td {TD} style="padding:10px 14px;border-bottom:1px solid rgba(148,163,184,0.04);
          font-family:'DM Mono',monospace;font-size:12px;color:#5A8AA8;">{int(row['id'])}</td>
      <td {TD} style="padding:10px 14px;border-bottom:1px solid rgba(148,163,184,0.04);
          font-size:12px;color:#6B9AB8;white-space:nowrap;">{row['created_at']}</td>
      <td {TD} style="padding:10px 14px;border-bottom:1px solid rgba(148,163,184,0.04);
          font-family:'DM Mono',monospace;font-size:12px;color:#5A8AA8;">{row['ml_probability']:.4f}</td>
      <td {TD} style="padding:10px 14px;border-bottom:1px solid rgba(148,163,184,0.04);">{rbadge(row['ml_risk_level'])}</td>
      <td {TD} style="padding:10px 14px;border-bottom:1px solid rgba(148,163,184,0.04);">{rbadge(row['final_risk_level'])}</td>
      <td {TD} style="padding:10px 14px;border-bottom:1px solid rgba(148,163,184,0.04);
          font-family:'DM Mono',monospace;font-size:13px;font-weight:700;color:#C4CFDE;">{int(row['final_risk_score'])}</td>
      <td {TD} style="padding:10px 14px;border-bottom:1px solid rgba(148,163,184,0.04);
          text-align:center;">{ov}</td>
    </tr>"""

st.markdown(f"""
<div style="background:rgba(6,9,18,0.92);border:1px solid rgba(148,163,184,0.09);
            border-radius:16px;overflow:hidden;overflow-x:auto;">
  <table style="width:100%;border-collapse:collapse;min-width:700px;">
    <thead><tr style="background:rgba(3,5,12,0.7);">{th}</tr></thead>
    <tbody>{tbody}</tbody>
  </table>
</div>
""", unsafe_allow_html=True)

# ── FOOTER ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;font-size:12px;color:#1A2535;letter-spacing:0.06em;
            padding:2.5rem 0 1.5rem;display:flex;align-items:center;
            justify-content:center;gap:10px;">
  <span style="width:3px;height:3px;border-radius:50%;background:#1A2535;display:inline-block;"></span>
  Fraud Intelligence Platform &nbsp;·&nbsp; ML + Python + Streamlit
  <span style="width:3px;height:3px;border-radius:50%;background:#1A2535;display:inline-block;"></span>
</div>
""", unsafe_allow_html=True)
def inject_premium_design():
    import streamlit as st

    st.markdown("""
    <style>

    /* ════════════════════════════════════════════
       FONTS
    ════════════════════════════════════════════ */
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;0,9..40,800;1,9..40,400&family=DM+Mono:wght@400;500&display=swap');

    /* ════════════════════════════════════════════
       GLOBAL
    ════════════════════════════════════════════ */
    *, *::before, *::after {
        font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
        -webkit-font-smoothing: antialiased !important;
        box-sizing: border-box;
    }

    /* ════════════════════════════════════════════
       BACKGROUND
    ════════════════════════════════════════════ */
    .stApp {
        background-color: #05080F !important;
        background-image:
            radial-gradient(ellipse 70% 45% at 5% 0%,   rgba(0,180,255,0.10)  0%, transparent 55%),
            radial-gradient(ellipse 55% 35% at 95% 100%, rgba(168,85,247,0.08) 0%, transparent 50%),
            radial-gradient(ellipse 40% 30% at 50% 50%,  rgba(0,229,160,0.03)  0%, transparent 60%);
        background-attachment: fixed;
    }

    .block-container {
        padding: 2.5rem 3.25rem 4rem !important;
        max-width: 1480px !important;
    }

    /* ════════════════════════════════════════════
       HEADER COMPONENTS
    ════════════════════════════════════════════ */
    @keyframes pulse {
        0%, 100% { opacity: 1; transform: scale(1); }
        50%       { opacity: 0.45; transform: scale(0.78); }
    }

    .live-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: rgba(0,180,255,0.10);
        border: 1px solid rgba(0,180,255,0.28);
        color: #60C8FF;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.15em;
        text-transform: uppercase;
        padding: 5px 14px;
        border-radius: 100px;
        margin-bottom: 18px;
    }

    .live-dot {
        display: inline-block;
        width: 6px; height: 6px;
        border-radius: 50%;
        background: #00B4FF;
        box-shadow: 0 0 8px #00B4FF;
        animation: pulse 2s ease-in-out infinite;
    }

    .page-title {
        font-size: 50px;
        font-weight: 800;
        line-height: 1.05;
        letter-spacing: -0.04em;
        color: #E8F0FF;
        margin-bottom: 12px;
    }

    .gradient-word {
        background: linear-gradient(118deg, #00B4FF 15%, #A855F7 85%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    .page-subtitle {
        font-size: 14px;
        color: #5A8AA8;
        font-weight: 400;
        letter-spacing: 0.01em;
    }

    /* ════════════════════════════════════════════
       DIVIDERS & SPACING
    ════════════════════════════════════════════ */
    .hdivider {
        height: 1px;
        background: linear-gradient(90deg,
            transparent 0%,
            rgba(0,180,255,0.12) 25%,
            rgba(168,85,247,0.10) 75%,
            transparent 100%);
        margin: 0 0 2.5rem;
    }

    .section-gap { height: 2rem; }

    hr { display: none !important; }

    .section-label {
        font-size: 11px;
        font-weight: 700;
        color: #5A8AA8;
        text-transform: uppercase;
        letter-spacing: 0.14em;
        margin-bottom: 1.25rem;
    }

    /* ════════════════════════════════════════════
       KPI CARDS
    ════════════════════════════════════════════ */
    .kpi-card {
        position: relative;
        overflow: hidden;
        background: rgba(8,13,26,0.88);
        border: 1px solid rgba(148,163,184,0.10);
        border-radius: 16px;
        padding: 22px 18px 18px;
        min-height: 148px;
        transition: transform 0.30s cubic-bezier(.4,0,.2,1),
                    border-color 0.30s ease,
                    box-shadow 0.30s ease;
        cursor: default;
    }

    .kpi-card:hover { transform: translateY(-5px); }

    /* top accent stripe */
    .kpi-stripe {
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 2px;
        border-radius: 16px 16px 0 0;
        opacity: 0.75;
    }

    /* glow blob bottom-right */
    .kpi-glow-blob {
        position: absolute;
        width: 110px; height: 110px;
        border-radius: 50%;
        bottom: -35px; right: -20px;
        opacity: 0.12;
        filter: blur(32px);
        pointer-events: none;
        transition: opacity 0.30s ease;
    }

    .kpi-card:hover .kpi-glow-blob { opacity: 0.28; }

    /* blue */
    .kpi-blue                  { border-color: rgba(0,180,255,0.18); }
    .kpi-blue:hover            { border-color: rgba(0,180,255,0.38); box-shadow: 0 8px 40px rgba(0,180,255,0.14); }
    .kpi-blue .kpi-stripe      { background: linear-gradient(90deg, transparent, #00B4FF, transparent); }
    .kpi-blue .kpi-glow-blob   { background: #00B4FF; }

    /* red */
    .kpi-red                   { border-color: rgba(255,45,85,0.18); }
    .kpi-red:hover             { border-color: rgba(255,45,85,0.38); box-shadow: 0 8px 40px rgba(255,45,85,0.14); }
    .kpi-red .kpi-stripe       { background: linear-gradient(90deg, transparent, #FF2D55, transparent); }
    .kpi-red .kpi-glow-blob    { background: #FF2D55; }

    /* orange */
    .kpi-orange                { border-color: rgba(255,138,0,0.18); }
    .kpi-orange:hover          { border-color: rgba(255,138,0,0.38); box-shadow: 0 8px 40px rgba(255,138,0,0.14); }
    .kpi-orange .kpi-stripe    { background: linear-gradient(90deg, transparent, #FF8A00, transparent); }
    .kpi-orange .kpi-glow-blob { background: #FF8A00; }

    /* purple */
    .kpi-purple                { border-color: rgba(168,85,247,0.18); }
    .kpi-purple:hover          { border-color: rgba(168,85,247,0.38); box-shadow: 0 8px 40px rgba(168,85,247,0.14); }
    .kpi-purple .kpi-stripe    { background: linear-gradient(90deg, transparent, #A855F7, transparent); }
    .kpi-purple .kpi-glow-blob { background: #A855F7; }

    /* teal */
    .kpi-teal                  { border-color: rgba(0,229,160,0.18); }
    .kpi-teal:hover            { border-color: rgba(0,229,160,0.38); box-shadow: 0 8px 40px rgba(0,229,160,0.14); }
    .kpi-teal .kpi-stripe      { background: linear-gradient(90deg, transparent, #00E5A0, transparent); }
    .kpi-teal .kpi-glow-blob   { background: #00E5A0; }

    .kpi-label {
        font-size: 10px;
        font-weight: 700;
        color: #6A9AB8;
        text-transform: uppercase;
        letter-spacing: 0.14em;
        margin-bottom: 12px;
    }

    .kpi-value {
        font-size: 38px;
        font-weight: 800;
        color: #E8F0FF;
        letter-spacing: -0.04em;
        line-height: 1;
        font-variant-numeric: tabular-nums;
        margin-bottom: 9px;
    }

    .kpi-sub {
        font-size: 11px;
        font-weight: 500;
        color: #4E7A96;
        letter-spacing: 0.01em;
    }

    /* ════════════════════════════════════════════
       CHART CARDS
    ════════════════════════════════════════════ */
    .chart-card {
        background: rgba(8,13,26,0.88);
        border: 1px solid rgba(148,163,184,0.09);
        border-radius: 16px;
        padding: 22px 20px 10px;
    }

    .chart-card-title {
        font-size: 11px;
        font-weight: 700;
        color: #5A8AA8;
        text-transform: uppercase;
        letter-spacing: 0.13em;
        margin-bottom: 4px;
    }

    /* ════════════════════════════════════════════
       OVERRIDE TRIGGER ROWS
    ════════════════════════════════════════════ */
    .trigger-row {
        display: flex;
        align-items: center;
        gap: 14px;
        padding: 9px 0;
        border-bottom: 1px solid rgba(148,163,184,0.05);
    }
    .trigger-row:last-child { border-bottom: none; }

    .trigger-label {
        font-size: 12px;
        font-weight: 500;
        color: #7A9DB8;
        min-width: 220px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .trigger-bar-wrap {
        flex: 1;
        height: 5px;
        background: rgba(148,163,184,0.07);
        border-radius: 100px;
        overflow: hidden;
    }

    .trigger-bar {
        height: 100%;
        background: linear-gradient(90deg, #00B4FF, #A855F7);
        border-radius: 100px;
    }

    .trigger-stat {
        min-width: 80px;
        display: flex;
        align-items: center;
        gap: 8px;
        justify-content: flex-end;
    }

    .trigger-count {
        font-size: 12px;
        font-weight: 700;
        color: #8899AA;
        font-variant-numeric: tabular-nums;
        font-family: 'DM Mono', monospace !important;
    }

    .trigger-pct {
        font-size: 11px;
        color: #5A8AA8;
    }

    /* ════════════════════════════════════════════
       BUTTON
    ════════════════════════════════════════════ */
    .stButton > button {
        background: rgba(0,180,255,0.08) !important;
        color: #60C8FF !important;
        border: 1px solid rgba(0,180,255,0.25) !important;
        border-radius: 10px !important;
        padding: 0.75rem 1.5rem !important;
        font-weight: 600 !important;
        font-size: 13px !important;
        letter-spacing: 0.03em !important;
        transition: all 0.25s ease !important;
        box-shadow: none !important;
    }

    .stButton > button:hover {
        background: rgba(0,180,255,0.16) !important;
        border-color: rgba(0,180,255,0.50) !important;
        color: #A8DFFF !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(0,180,255,0.18) !important;
    }

    /* ════════════════════════════════════════════
       INFO BOX
    ════════════════════════════════════════════ */
    [data-testid="stAlert"] {
        background: rgba(0,180,255,0.07) !important;
        border: 1px solid rgba(0,180,255,0.20) !important;
        border-left: 3px solid #00B4FF !important;
        border-radius: 10px !important;
        color: #6B8099 !important;
    }

    /* ════════════════════════════════════════════
       HIDE STREAMLIT CHROME
    ════════════════════════════════════════════ */
    #MainMenu, footer, header           { visibility: hidden !important; }
    [data-testid="stDecoration"]        { display: none !important; }
    [data-testid="stStatusWidget"]      { visibility: hidden !important; }

    /* ════════════════════════════════════════════
       SCROLLBAR
    ════════════════════════════════════════════ */
    ::-webkit-scrollbar       { width: 5px; height: 5px; }
    ::-webkit-scrollbar-track { background: #05080F; }
    ::-webkit-scrollbar-thumb { background: rgba(148,163,184,0.15); border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(148,163,184,0.30); }

    </style>
    """, unsafe_allow_html=True)
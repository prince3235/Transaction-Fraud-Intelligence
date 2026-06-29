def inject_premium_design():
    import streamlit as st

    st.markdown("""
    <style>

    /* ════════════════════════════════════════════
       FONTS (Modern Clean Look - Inter/DM Sans)
    ════════════════════════════════════════════ */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap');

    /* ════════════════════════════════════════════
       GLOBAL
    ════════════════════════════════════════════ */
    *, *::before, *::after {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        -webkit-font-smoothing: antialiased !important;
        box-sizing: border-box;
    }

    /* ════════════════════════════════════════════
       BACKGROUND & LAYOUT
    ════════════════════════════════════════════ */
    .stApp {
        background-color: #FAFAFA !important;
        background-image: 
            radial-gradient(ellipse at top right, rgba(37,99,235,0.03) 0%, transparent 40%),
            radial-gradient(ellipse at bottom left, rgba(16,185,129,0.02) 0%, transparent 40%);
        background-attachment: fixed;
    }

    .block-container {
        padding: 2.5rem 3.25rem 4rem !important;
        max-width: 1480px !important;
    }
    
    [data-testid="stSidebar"] {
        background-color: #F8FAFC !important;
        border-right: 1px solid #E2E8F0 !important;
    }

    /* ════════════════════════════════════════════
       HEADER COMPONENTS
    ════════════════════════════════════════════ */
    @keyframes pulse {
        0%, 100% { opacity: 1; transform: scale(1); }
        50%       { opacity: 0.7; transform: scale(0.9); }
    }

    .live-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: #EFF6FF;
        border: 1px solid #BFDBFE;
        color: #2563EB;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        padding: 5px 14px;
        border-radius: 100px;
        margin-bottom: 18px;
    }

    .live-dot {
        display: inline-block;
        width: 6px; height: 6px;
        border-radius: 50%;
        background: #2563EB;
        box-shadow: 0 0 6px rgba(37,99,235,0.5);
        animation: pulse 2s ease-in-out infinite;
    }

    .page-title {
        font-size: 46px;
        font-weight: 800;
        line-height: 1.1;
        letter-spacing: -0.03em;
        color: #0F172A;
        margin-bottom: 12px;
    }

    .gradient-word {
        background: linear-gradient(135deg, #2563EB 0%, #7C3AED 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    .page-subtitle {
        font-size: 15px;
        color: #64748B;
        font-weight: 400;
        letter-spacing: 0.01em;
    }

    /* ════════════════════════════════════════════
       DIVIDERS & SPACING
    ════════════════════════════════════════════ */
    .hdivider {
        height: 1px;
        background: #E2E8F0;
        margin: 2rem 0;
        width: 100%;
    }

    .section-gap {
        height: 2.5rem;
    }

    .section-label {
        font-size: 13px;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: #94A3B8;
        margin-bottom: 1.25rem;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .section-label::after {
        content: '';
        flex: 1;
        height: 1px;
        background: #F1F5F9;
    }

    /* ════════════════════════════════════════════
       CARDS & CONTAINERS (Light UI)
    ════════════════════════════════════════════ */
    .metric-card, .kpi-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 22px;
        position: relative;
        overflow: hidden;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05), 0 2px 4px -1px rgba(0,0,0,0.03);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    
    .metric-card:hover, .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0,0,0,0.08), 0 4px 6px -2px rgba(0,0,0,0.04);
    }

    .metric-label, .kpi-label {
        font-size: 12px;
        color: #64748B;
        text-transform: uppercase;
        font-weight: 600;
        letter-spacing: 0.05em;
        margin-bottom: 12px;
        z-index: 2;
        position: relative;
    }

    .metric-value, .kpi-value {
        font-size: 32px;
        font-weight: 800;
        color: #0F172A;
        line-height: 1;
        z-index: 2;
        position: relative;
        font-family: 'Inter', sans-serif;
    }

    .kpi-sub {
        font-size: 12px;
        color: #94A3B8;
        margin-top: 10px;
        font-weight: 500;
        z-index: 2;
        position: relative;
    }

    /* Colored Accents for Cards */
    .kpi-blue { border-bottom: 3px solid #3B82F6; }
    .kpi-purple { border-bottom: 3px solid #8B5CF6; }
    .kpi-orange { border-bottom: 3px solid #F59E0B; }
    .kpi-teal { border-bottom: 3px solid #10B981; }

    .kpi-stripe {
        position: absolute;
        top: 0; left: 0; bottom: 0; width: 4px;
        background: transparent; /* Removed side stripe in favor of bottom accent */
    }

    /* ════════════════════════════════════════════
       STREAMLIT NATIVE OVERRIDES (Light Mode)
    ════════════════════════════════════════════ */
    /* Metric widget */
    [data-testid="stMetricValue"] {
        font-family: 'Inter', sans-serif !important;
        font-weight: 800 !important;
        font-size: 30px !important;
        color: #0F172A !important;
    }
    [data-testid="stMetricLabel"] {
        color: #64748B !important;
        font-size: 13px !important;
        font-weight: 600 !important;
    }

    /* DataFrames */
    .stDataFrame {
        border-radius: 10px;
        overflow: hidden;
        border: 1px solid #E2E8F0 !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    [data-testid="stDataFrame"] table {
        color: #334155;
        background-color: #FFFFFF !important;
    }
    [data-testid="stDataFrame"] th {
        background-color: #F8FAFC !important;
        color: #475569 !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        font-size: 11px;
        letter-spacing: 0.05em;
        border-bottom: 1px solid #E2E8F0 !important;
    }
    [data-testid="stDataFrame"] td {
        border-bottom: 1px solid #F1F5F9 !important;
        font-size: 13px !important;
    }

    /* Buttons */
    .stButton > button {
        background: #FFFFFF !important;
        border: 1px solid #CBD5E1 !important;
        color: #334155 !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
        padding: 0.5rem 1rem !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
    }
    .stButton > button:hover {
        background: #F8FAFC !important;
        border-color: #94A3B8 !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05) !important;
    }
    
    /* Primary Button override */
    .stButton > button[kind="primary"] {
        background: #2563EB !important;
        border: 1px solid #1D4ED8 !important;
        color: #FFFFFF !important;
        box-shadow: 0 2px 4px rgba(37,99,235,0.2) !important;
    }
    .stButton > button[kind="primary"]:hover {
        background: #1D4ED8 !important;
        box-shadow: 0 4px 6px rgba(37,99,235,0.3) !important;
    }

    /* Inputs */
    .stTextInput > div > div > input,
    .stSelectbox > div > div > div {
        background-color: #FFFFFF !important;
        border: 1px solid #CBD5E1 !important;
        color: #0F172A !important;
        border-radius: 8px !important;
        font-size: 14px !important;
        box-shadow: inset 0 1px 2px rgba(0,0,0,0.02) !important;
    }
    .stTextInput > div > div > input:focus,
    .stSelectbox > div > div > div:focus-within {
        border-color: #3B82F6 !important;
        box-shadow: 0 0 0 3px rgba(59,130,246,0.1) !important;
    }

    /* Fix dark mode text inside custom HTML elements */
    div[style*="background:rgba(8,13,26"] {
        background: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05) !important;
    }
    div[style*="color:#E8F0FF"] { color: #0F172A !important; }
    div[style*="color:#BAC4D0"] { color: #475569 !important; }
    div[style*="color:#8899AA"] { color: #64748B !important; }
    
    /* specific color fixes for status tags */
    div[style*="color:#00E676"], span[style*="color:#00E676"] { color: #10B981 !important; }
    div[style*="color:#FF2D55"], span[style*="color:#FF2D55"] { color: #EF4444 !important; }
    div[style*="color:#FF8A00"], span[style*="color:#FF8A00"] { color: #F59E0B !important; }
    div[style*="color:#00B4FF"], span[style*="color:#00B4FF"] { color: #3B82F6 !important; }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
        border-bottom: 1px solid #E2E8F0;
    }
    .stTabs [data-baseweb="tab"] {
        padding-top: 12px;
        padding-bottom: 12px;
        color: #64748B !important;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        color: #2563EB !important;
        border-bottom-color: #2563EB !important;
    }

    /* Custom inline tags */
    .status-tag {
        font-size: 11px;
        font-weight: 700;
        padding: 3px 8px;
        border-radius: 4px;
        text-transform: uppercase;
        display: inline-block;
    }
    .tag-green { background: #DCFCE7; color: #16A34A; border: 1px solid #BBF7D0; }
    .tag-red { background: #FEE2E2; color: #DC2626; border: 1px solid #FECACA; }
    .tag-orange { background: #FEF3C7; color: #D97706; border: 1px solid #FDE68A; }
    
    /* Code blocks / JSON viewer */
    pre {
        background-color: #F8FAFC !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 8px !important;
    }
    code {
        color: #334155 !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 13px !important;
    }

    </style>
    """, unsafe_allow_html=True)
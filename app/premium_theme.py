def inject_premium_theme():
    import streamlit as st
    
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
    
    /* ========== GLOBAL RESET ========== */
    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    
    .stApp {
        background: #0B1220;
        background-image: 
            radial-gradient(at 0% 0%, rgba(30, 41, 59, 0.6) 0px, transparent 50%),
            radial-gradient(at 100% 100%, rgba(51, 65, 85, 0.5) 0px, transparent 50%);
    }
    
    /* ========== CONTAINERS ========== */
    .block-container {
        padding: 2rem 3rem !important;
        max-width: 1400px !important;
    }
    
    /* ========== HEADERS ========== */
    h1 {
        font-size: 2.5rem !important;
        font-weight: 800 !important;
        color: #F8FAFC !important;
        letter-spacing: -0.04em !important;
        margin-bottom: 0.25rem !important;
        background: linear-gradient(135deg, #F8FAFC 0%, #CBD5E1 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        text-shadow: 0 0 60px rgba(59, 130, 246, 0.15);
    }
    
    h2 {
        font-size: 1.25rem !important;
        font-weight: 600 !important;
        color: #E2E8F0 !important;
        margin-top: 2rem !important;
        margin-bottom: 1rem !important;
    }
    
    h3 {
        font-size: 1rem !important;
        font-weight: 600 !important;
        color: #CBD5E1 !important;
        letter-spacing: -0.01em !important;
    }
    
    /* ========== METRIC CARDS (Enhanced Glow) ========== */
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, 
            rgba(30, 41, 59, 0.7) 0%, 
            rgba(51, 65, 85, 0.5) 100%);
        backdrop-filter: blur(32px);
        -webkit-backdrop-filter: blur(32px);
        border: 1px solid rgba(148, 163, 184, 0.15);
        border-radius: 18px;
        padding: 2rem !important;
        box-shadow: 
            0 10px 30px rgba(0, 0, 0, 0.25),
            inset 0 1px 0 rgba(255, 255, 255, 0.08);
    }
    
    [data-testid="stMetric"]:hover {
        transform: translateY(-8px) scale(1.03);
        border-color: rgba(59, 130, 246, 0.5);
        box-shadow: 
            0 20px 50px rgba(59, 130, 246, 0.25),
            0 0 100px rgba(59, 130, 246, 0.15),
            inset 0 1px 0 rgba(255, 255, 255, 0.15);
    }
    
    [data-testid="stMetricLabel"] {
        font-size: 0.75rem !important;
        font-weight: 600 !important;
        color: #94A3B8 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.1em !important;
        margin-bottom: 0.75rem !important;
    }
    
    [data-testid="stMetricValue"] {
        font-size: 2.5rem !important;
        font-weight: 900 !important;
        color: #F8FAFC !important;
        line-height: 1 !important;
        letter-spacing: -0.03em !important;
    }
    
    [data-testid="stMetricDelta"] {
        font-size: 0.75rem !important;
        font-weight: 500 !important;
        margin-top: 0.75rem !important;
        opacity: 0.85;
    }
    
    /* ========== DIVIDERS ========== */
    hr {
        margin: 3rem 0 !important;
        border: none !important;
        height: 1px !important;
        background: linear-gradient(90deg, 
            transparent 0%, 
            rgba(148, 163, 184, 0.25) 50%, 
            transparent 100%) !important;
    }
    
    /* ========== BUTTONS ========== */
    .stButton > button {
        background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.75rem 1.75rem !important;
        font-weight: 700 !important;
        font-size: 0.875rem !important;
        letter-spacing: 0.03em !important;
        box-shadow: 
            0 6px 16px rgba(59, 130, 246, 0.35),
            inset 0 1px 0 rgba(255, 255, 255, 0.25) !important;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%) !important;
        box-shadow: 
            0 8px 24px rgba(59, 130, 246, 0.45),
            0 0 50px rgba(59, 130, 246, 0.25),
            inset 0 1px 0 rgba(255, 255, 255, 0.35) !important;
        transform: translateY(-3px) scale(1.03) !important;
    }
    
    /* ========== DATAFRAME (CRITICAL FIX) ========== */
    [data-testid="stDataFrame"] {
        background: rgba(15, 23, 42, 0.6) !important;
        border: 1px solid rgba(148, 163, 184, 0.12) !important;
        border-radius: 16px !important;
        overflow: hidden !important;
        box-shadow: 
            0 8px 24px rgba(0, 0, 0, 0.3),
            inset 0 1px 0 rgba(255, 255, 255, 0.05) !important;
    }
    
    [data-testid="stDataFrame"] > div {
        background: transparent !important;
    }
    
    [data-testid="stDataFrame"] table {
        color: #E2E8F0 !important;
        font-size: 0.875rem !important;
        background: transparent !important;
    }
    
    [data-testid="stDataFrame"] thead {
        background: rgba(30, 41, 59, 0.8) !important;
        border-bottom: 1px solid rgba(148, 163, 184, 0.2) !important;
    }
    
    [data-testid="stDataFrame"] thead th {
        font-size: 0.75rem !important;
        font-weight: 700 !important;
        color: #94A3B8 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.1em !important;
        padding: 1rem !important;
        background: transparent !important;
    }
    
    [data-testid="stDataFrame"] tbody tr {
        border-bottom: 1px solid rgba(148, 163, 184, 0.08) !important;
        background: transparent !important;
    }
    
    [data-testid="stDataFrame"] tbody tr:nth-child(even) {
        background: rgba(51, 65, 85, 0.15) !important;
    }
    
    [data-testid="stDataFrame"] tbody tr:hover {
        background: rgba(59, 130, 246, 0.1) !important;
        transform: scale(1.005);
        box-shadow: inset 0 0 0 1px rgba(59, 130, 246, 0.2);
    }
    
    [data-testid="stDataFrame"] tbody td {
        font-size: 0.875rem !important;
        color: #CBD5E1 !important;
        padding: 1rem !important;
        background: transparent !important;
    }
    
    /* ========== CAPTIONS ========== */
    .caption {
        font-size: 0.875rem;
        color: #64748B;
        font-weight: 400;
        margin-top: 0.5rem;
    }
    
    /* ========== SUBTITLE ========== */
    .subtitle {
        font-size: 1.05rem;
        font-weight: 500;
        color: #94A3B8;
        margin-top: 0.5rem;
        letter-spacing: 0.02em;
    }
    
    /* ========== BADGES ========== */
    .badge {
        display: inline-block;
        padding: 0.4rem 0.9rem;
        border-radius: 10px;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }
    
    .badge-critical {
        background: rgba(220, 38, 38, 0.2);
        color: #FCA5A5;
        border: 1px solid rgba(220, 38, 38, 0.35);
        box-shadow: 0 2px 10px rgba(220, 38, 38, 0.2);
    }
    
    .badge-high {
        background: rgba(234, 88, 12, 0.2);
        color: #FDBA74;
        border: 1px solid rgba(234, 88, 12, 0.35);
        box-shadow: 0 2px 10px rgba(234, 88, 12, 0.2);
    }
    
    .badge-medium {
        background: rgba(202, 138, 4, 0.2);
        color: #FCD34D;
        border: 1px solid rgba(202, 138, 4, 0.35);
        box-shadow: 0 2px 10px rgba(202, 138, 4, 0.2);
    }
    
    .badge-low {
        background: rgba(34, 197, 94, 0.2);
        color: #86EFAC;
        border: 1px solid rgba(34, 197, 94, 0.35);
        box-shadow: 0 2px 10px rgba(34, 197, 94, 0.2);
    }
    
    /* ========== SIDEBAR ========== */
    [data-testid="stSidebar"] {
        background: rgba(15, 23, 42, 0.98) !important;
        backdrop-filter: blur(32px) !important;
        border-right: 1px solid rgba(148, 163, 184, 0.15) !important;
    }
    
    /* ========== INFO BOXES ========== */
    .stInfo, .stWarning, .stSuccess {
        background: rgba(59, 130, 246, 0.15) !important;
        border-left: 3px solid #3B82F6 !important;
        border-radius: 12px !important;
        color: #E2E8F0 !important;
        backdrop-filter: blur(12px) !important;
    }
    
    /* ========== REMOVE STREAMLIT BRANDING ========== */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)
def inject_premium_theme():
    import streamlit as st
    
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* ========== GLOBAL RESET ========== */
    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }
    
    .stApp {
        background: #0B1220;
        background-image: radial-gradient(at 0% 0%, rgba(30, 41, 59, 0.4) 0px, transparent 50%),
                          radial-gradient(at 100% 100%, rgba(51, 65, 85, 0.3) 0px, transparent 50%);
    }
    
    /* ========== CONTAINERS ========== */
    .block-container {
        padding: 2rem 3rem !important;
        max-width: 1400px !important;
    }
    
    /* ========== HEADERS ========== */
    h1 {
        font-size: 2rem !important;
        font-weight: 700 !important;
        color: #F1F5F9 !important;
        letter-spacing: -0.02em !important;
        margin-bottom: 0.5rem !important;
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
    }
    
    /* ========== METRIC CARDS (Premium Style) ========== */
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.5) 0%, rgba(51, 65, 85, 0.3) 100%);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(148, 163, 184, 0.1);
        border-radius: 16px;
        padding: 1.5rem !important;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    [data-testid="stMetric"]:hover {
        transform: translateY(-4px);
        border-color: rgba(59, 130, 246, 0.3);
        box-shadow: 0 12px 32px rgba(59, 130, 246, 0.15);
    }
    
    [data-testid="stMetricLabel"] {
        font-size: 0.75rem !important;
        font-weight: 500 !important;
        color: #94A3B8 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
        margin-bottom: 0.5rem !important;
    }
    
    [data-testid="stMetricValue"] {
        font-size: 2rem !important;
        font-weight: 700 !important;
        color: #F1F5F9 !important;
        line-height: 1 !important;
    }
    
    [data-testid="stMetricDelta"] {
        font-size: 0.75rem !important;
        font-weight: 500 !important;
        margin-top: 0.5rem !important;
    }
    
    /* ========== DIVIDERS ========== */
    hr {
        margin: 2.5rem 0 !important;
        border: none !important;
        height: 1px !important;
        background: linear-gradient(90deg, 
            transparent 0%, 
            rgba(148, 163, 184, 0.15) 50%, 
            transparent 100%) !important;
    }
    
    /* ========== BUTTONS ========== */
    .stButton > button {
        background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 0.625rem 1.25rem !important;
        font-weight: 600 !important;
        font-size: 0.875rem !important;
        letter-spacing: 0.01em !important;
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.25) !important;
        transition: all 0.2s ease !important;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%) !important;
        box-shadow: 0 6px 16px rgba(59, 130, 246, 0.35) !important;
        transform: translateY(-1px) !important;
    }
    
    /* ========== DATAFRAME ========== */
    [data-testid="stDataFrame"] {
        background: rgba(30, 41, 59, 0.3) !important;
        border: 1px solid rgba(148, 163, 184, 0.1) !important;
        border-radius: 12px !important;
        overflow: hidden !important;
    }
    
    [data-testid="stDataFrame"] table {
        color: #E2E8F0 !important;
    }
    
    [data-testid="stDataFrame"] thead {
        background: rgba(51, 65, 85, 0.5) !important;
        border-bottom: 1px solid rgba(148, 163, 184, 0.15) !important;
    }
    
    [data-testid="stDataFrame"] thead th {
        font-size: 0.75rem !important;
        font-weight: 600 !important;
        color: #94A3B8 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
        padding: 0.75rem !important;
    }
    
    [data-testid="stDataFrame"] tbody tr {
        border-bottom: 1px solid rgba(148, 163, 184, 0.06) !important;
        transition: background 0.15s ease !important;
    }
    
    [data-testid="stDataFrame"] tbody tr:hover {
        background: rgba(59, 130, 246, 0.05) !important;
    }
    
    [data-testid="stDataFrame"] tbody td {
        font-size: 0.875rem !important;
        color: #CBD5E1 !important;
        padding: 0.875rem !important;
    }
    
    /* ========== CAPTIONS ========== */
    .caption {
        font-size: 0.875rem;
        color: #64748B;
        font-weight: 400;
        margin-top: 0.25rem;
    }
    
    /* ========== BADGES ========== */
    .badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 8px;
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 0.02em;
    }
    
    .badge-critical {
        background: rgba(239, 68, 68, 0.15);
        color: #FCA5A5;
        border: 1px solid rgba(239, 68, 68, 0.25);
    }
    
    .badge-high {
        background: rgba(249, 115, 22, 0.15);
        color: #FDBA74;
        border: 1px solid rgba(249, 115, 22, 0.25);
    }
    
    .badge-medium {
        background: rgba(245, 158, 11, 0.15);
        color: #FCD34D;
        border: 1px solid rgba(245, 158, 11, 0.25);
    }
    
    .badge-low {
        background: rgba(34, 197, 94, 0.15);
        color: #86EFAC;
        border: 1px solid rgba(34, 197, 94, 0.25);
    }
    
    /* ========== SIDEBAR ========== */
    [data-testid="stSidebar"] {
        background: rgba(15, 23, 42, 0.95) !important;
        backdrop-filter: blur(20px) !important;
        border-right: 1px solid rgba(148, 163, 184, 0.1) !important;
    }
    
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        color: #CBD5E1 !important;
    }
    
    /* ========== INFO BOXES ========== */
    .stInfo, .stWarning, .stSuccess {
        background: rgba(59, 130, 246, 0.1) !important;
        border-left: 3px solid #3B82F6 !important;
        border-radius: 8px !important;
        color: #E2E8F0 !important;
    }
    
    /* ========== CLEAN SPACING ========== */
    .element-container {
        margin-bottom: 0 !important;
    }
    
    /* ========== REMOVE STREAMLIT BRANDING ========== */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)
def inject_premium_design():
    import streamlit as st
    
    st.markdown("""
    <style>
    /* ========== FONT IMPORT ========== */
    @import url('https://rsms.me/inter/inter.css');
    
    /* ========== GLOBAL RESET ========== */
    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
    }
    
    /* ========== ROOT VARIABLES ========== */
    :root {
        --bg-primary: #0A0E1A;
        --bg-secondary: #0F1419;
        --bg-card: rgba(17, 24, 39, 0.6);
        --border-subtle: rgba(148, 163, 184, 0.08);
        --border-medium: rgba(148, 163, 184, 0.15);
        --text-primary: #F1F5F9;
        --text-secondary: #CBD5E1;
        --text-tertiary: #94A3B8;
        --accent-blue: #3B82F6;
        --accent-blue-hover: #2563EB;
        --shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.15);
        --shadow-md: 0 8px 24px rgba(0, 0, 0, 0.2);
        --shadow-lg: 0 16px 40px rgba(0, 0, 0, 0.3);
        --shadow-glow: 0 0 60px rgba(59, 130, 246, 0.15);
        --radius-sm: 8px;
        --radius-md: 12px;
        --radius-lg: 16px;
    }
    
    /* ========== APP BACKGROUND ========== */
    .stApp {
        background: var(--bg-primary);
        background-image: 
            radial-gradient(at 0% 0%, rgba(59, 130, 246, 0.08) 0px, transparent 50%),
            radial-gradient(at 100% 100%, rgba(99, 102, 241, 0.06) 0px, transparent 50%);
    }
    
    /* ========== CONTAINER ========== */
    .block-container {
        padding: 2.5rem 3rem !important;
        max-width: 1440px !important;
    }
    
    /* ========== TYPOGRAPHY SYSTEM ========== */
    h1 {
        font-size: 2.75rem !important;
        font-weight: 800 !important;
        color: var(--text-primary) !important;
        letter-spacing: -0.05em !important;
        margin-bottom: 0.5rem !important;
        line-height: 1.1 !important;
        background: linear-gradient(135deg, #F8FAFC 20%, #94A3B8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    h2 {
        font-size: 1.375rem !important;
        font-weight: 600 !important;
        color: var(--text-secondary) !important;
        margin-top: 2.5rem !important;
        margin-bottom: 1.25rem !important;
        letter-spacing: -0.02em !important;
    }
    
    h3 {
        font-size: 1.125rem !important;
        font-weight: 600 !important;
        color: var(--text-secondary) !important;
        letter-spacing: -0.01em !important;
    }
    
    /* ========== SUBTITLE ========== */
    .subtitle {
        font-size: 1.125rem;
        font-weight: 500;
        color: var(--text-tertiary);
        margin-top: 0.75rem;
        letter-spacing: 0.01em;
    }
    
    /* ========== PREMIUM METRIC CARDS ========== */
    [data-testid="stMetric"] {
        background: linear-gradient(
            135deg,
            rgba(30, 41, 59, 0.8) 0%,
            rgba(51, 65, 85, 0.6) 100%
        );
        backdrop-filter: blur(40px) saturate(150%);
        -webkit-backdrop-filter: blur(40px) saturate(150%);
        border: 1px solid var(--border-medium);
        border-radius: var(--radius-lg);
        padding: 2rem 1.75rem !important;
        box-shadow: 
            var(--shadow-md),
            inset 0 1px 0 rgba(255, 255, 255, 0.08);
        position: relative;
        overflow: hidden;
        transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    }
    
    /* Subtle gradient overlay */
    [data-testid="stMetric"]::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 2px;
        background: linear-gradient(90deg, 
            transparent,
            var(--accent-blue),
            transparent
        );
        opacity: 0;
        transition: opacity 0.4s ease;
    }
    
    [data-testid="stMetric"]:hover {
        transform: translateY(-8px) scale(1.02);
        border-color: rgba(59, 130, 246, 0.4);
        box-shadow: 
            0 20px 50px rgba(59, 130, 246, 0.2),
            var(--shadow-glow),
            inset 0 1px 0 rgba(255, 255, 255, 0.12);
    }
    
    [data-testid="stMetric"]:hover::before {
        opacity: 1;
    }
    
    [data-testid="stMetricLabel"] {
        font-size: 0.8125rem !important;
        font-weight: 600 !important;
        color: var(--text-tertiary) !important;
        text-transform: uppercase !important;
        letter-spacing: 0.12em !important;
        margin-bottom: 0.875rem !important;
    }
    
    [data-testid="stMetricValue"] {
        font-size: 2.75rem !important;
        font-weight: 800 !important;
        color: var(--text-primary) !important;
        line-height: 1 !important;
        letter-spacing: -0.04em !important;
        font-variant-numeric: tabular-nums;
    }
    
    [data-testid="stMetricDelta"] {
        font-size: 0.8125rem !important;
        font-weight: 600 !important;
        margin-top: 0.875rem !important;
        opacity: 0.9;
    }
    
    /* ========== DIVIDER ========== */
    hr {
        margin: 3.5rem 0 !important;
        border: none !important;
        height: 1px !important;
        background: linear-gradient(
            90deg,
            transparent 0%,
            var(--border-medium) 50%,
            transparent 100%
        ) !important;
    }
    
    /* ========== PREMIUM BUTTON ========== */
    .stButton > button {
        background: linear-gradient(135deg, var(--accent-blue) 0%, var(--accent-blue-hover) 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: var(--radius-md) !important;
        padding: 0.875rem 2rem !important;
        font-weight: 700 !important;
        font-size: 0.9375rem !important;
        letter-spacing: 0.02em !important;
        box-shadow: 
            0 6px 20px rgba(59, 130, 246, 0.3),
            inset 0 1px 0 rgba(255, 255, 255, 0.2) !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, var(--accent-blue-hover) 0%, #1D4ED8 100%) !important;
        box-shadow: 
            0 10px 30px rgba(59, 130, 246, 0.4),
            0 0 60px rgba(59, 130, 246, 0.2),
            inset 0 1px 0 rgba(255, 255, 255, 0.3) !important;
        transform: translateY(-3px) scale(1.02) !important;
    }
    
    /* ========== PREMIUM TABLE ========== */
    [data-testid="stDataFrame"] {
        background: rgba(17, 24, 39, 0.7) !important;
        backdrop-filter: blur(20px) !important;
        border: 1px solid var(--border-medium) !important;
        border-radius: var(--radius-lg) !important;
        overflow: hidden !important;
        box-shadow: var(--shadow-md) !important;
    }
    
    [data-testid="stDataFrame"] > div {
        background: transparent !important;
    }
    
    [data-testid="stDataFrame"] table {
        color: var(--text-secondary) !important;
        background: transparent !important;
    }
    
    [data-testid="stDataFrame"] thead {
        background: rgba(30, 41, 59, 0.9) !important;
        border-bottom: 1px solid var(--border-medium) !important;
    }
    
    [data-testid="stDataFrame"] thead th {
        font-size: 0.8125rem !important;
        font-weight: 700 !important;
        color: var(--text-tertiary) !important;
        text-transform: uppercase !important;
        letter-spacing: 0.12em !important;
        padding: 1.125rem 1rem !important;
        background: transparent !important;
    }
    
    [data-testid="stDataFrame"] tbody tr {
        border-bottom: 1px solid rgba(148, 163, 184, 0.06) !important;
        background: transparent !important;
        transition: all 0.2s ease !important;
    }
    
    [data-testid="stDataFrame"] tbody tr:nth-child(odd) {
        background: rgba(51, 65, 85, 0.12) !important;
    }
    
    [data-testid="stDataFrame"] tbody tr:hover {
        background: rgba(59, 130, 246, 0.08) !important;
        transform: scale(1.002);
        box-shadow: inset 0 0 0 1px rgba(59, 130, 246, 0.2);
    }
    
    [data-testid="stDataFrame"] tbody td {
        font-size: 0.9375rem !important;
        color: var(--text-secondary) !important;
        padding: 1.125rem 1rem !important;
        background: transparent !important;
        font-variant-numeric: tabular-nums;
    }
    
    /* ========== BADGES ========== */
    .badge {
        display: inline-flex;
        align-items: center;
        padding: 0.4rem 0.95rem;
        border-radius: var(--radius-sm);
        font-size: 0.8125rem;
        font-weight: 700;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        transition: all 0.2s ease;
    }
    
    .badge-critical {
        background: linear-gradient(135deg, rgba(220, 38, 38, 0.2), rgba(185, 28, 28, 0.25));
        color: #FCA5A5;
        border: 1px solid rgba(220, 38, 38, 0.3);
        box-shadow: 0 2px 12px rgba(220, 38, 38, 0.15);
    }
    
    .badge-high {
        background: linear-gradient(135deg, rgba(234, 88, 12, 0.2), rgba(194, 65, 12, 0.25));
        color: #FDBA74;
        border: 1px solid rgba(234, 88, 12, 0.3);
        box-shadow: 0 2px 12px rgba(234, 88, 12, 0.15);
    }
    
    .badge-medium {
        background: linear-gradient(135deg, rgba(202, 138, 4, 0.2), rgba(161, 98, 7, 0.25));
        color: #FCD34D;
        border: 1px solid rgba(202, 138, 4, 0.3);
        box-shadow: 0 2px 12px rgba(202, 138, 4, 0.15);
    }
    
    .badge-low {
        background: linear-gradient(135deg, rgba(34, 197, 94, 0.2), rgba(22, 163, 74, 0.25));
        color: #86EFAC;
        border: 1px solid rgba(34, 197, 94, 0.3);
        box-shadow: 0 2px 12px rgba(34, 197, 94, 0.15);
    }
    
    /* ========== CAPTION ========== */
    .caption {
        font-size: 0.9375rem;
        color: var(--text-tertiary);
        font-weight: 500;
        margin-top: 0.5rem;
    }
    
    /* ========== INFO BOXES ========== */
    .stInfo {
        background: rgba(59, 130, 246, 0.12) !important;
        border: 1px solid rgba(59, 130, 246, 0.25) !important;
        border-left: 3px solid var(--accent-blue) !important;
        border-radius: var(--radius-md) !important;
        color: var(--text-secondary) !important;
        backdrop-filter: blur(8px) !important;
    }
    
    /* ========== HIDE STREAMLIT BRANDING ========== */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* ========== SCROLLBAR ========== */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: var(--bg-secondary);
    }
    
    ::-webkit-scrollbar-thumb {
        background: rgba(148, 163, 184, 0.3);
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: rgba(148, 163, 184, 0.5);
    }
    </style>
    """, unsafe_allow_html=True)
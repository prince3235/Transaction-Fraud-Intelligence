def inject_premium_design():
    import streamlit as st

    st.markdown("""
    <style>
    body, html {
        font-family: Inter, sans-serif;
    }

    .stApp {
        background: #0A0E1A;
    }

    h1 {
        font-size: 2.5rem;
        font-weight: 700;
        color: #F8FAFC;
    }

    .subtitle {
        color: #94A3B8;
    }

    [data-testid="stMetric"] {
        background: rgba(255,255,255,0.03);
        border-radius: 14px;
        padding: 1.5rem;
        border: 1px solid rgba(255,255,255,0.06);
    }

    [data-testid="stMetric"]:hover {
        transform: translateY(-4px);
        box-shadow: 0 10px 40px rgba(99,102,241,0.2);
    }

    [data-testid="stDataFrame"] {
        background: rgba(255,255,255,0.02);
        border-radius: 12px;
        border: 1px solid rgba(255,255,255,0.08);
    }

    </style>
    """, unsafe_allow_html=True)
import streamlit as st

def require_auth(permission: str = None) -> None:
    """
    Auto-bypassed auth guard. Automatically sets session to admin.
    """
    if "user" not in st.session_state or not st.session_state.user:
        st.session_state.user = {
            "id": 1,
            "username": "admin",
            "role": "admin"
        }
    pass

def display_user_profile():
    """Display a clean Admin badge instead of the complex profile card."""
    if "user" not in st.session_state or not st.session_state.user:
        st.session_state.user = {"id": 1, "username": "admin", "role": "admin"}
        
    st.sidebar.markdown(f"""
    <div style="background:#ffffff;border:1px solid #E2E8F0;
                border-radius:8px;padding:12px;margin-bottom:20px;
                box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
        <div style="font-size:14px;font-weight:700;color:#0F172A;">Admin Session</div>
        <div style="display:inline-block;background:#EFF6FF;
                    border:1px solid #BFDBFE;color:#2563EB;
                    font-size:10px;font-weight:700;letter-spacing:0.05em;
                    padding:2px 8px;border-radius:100px;margin-top:4px;">
            🛡️ FULL ACCESS
        </div>
    </div>
    """, unsafe_allow_html=True)

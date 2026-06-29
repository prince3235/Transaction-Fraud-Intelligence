import streamlit as st
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.auth import get_role_info, has_permission

def require_auth(permission: str = None) -> None:
    """
    Enforce authentication and optional RBAC permission on a Streamlit page.
    If the user is not authenticated or lacks permission, execution stops here.
    """
    if "user" not in st.session_state or not st.session_state.user:
        st.warning("Please log in to access this page.")
        if st.button("Go to Login"):
            st.switch_page("Home.py")
        st.stop()

    user = st.session_state.user
    
    if permission and not has_permission(user["role"], permission):
        st.error(f"Access Denied. You need the '{permission}' permission.")
        st.stop()

def display_user_profile():
    """Display the authenticated user's profile card in the sidebar."""
    if "user" not in st.session_state or not st.session_state.user:
        return
        
    user = st.session_state.user
    role_info = get_role_info(user["role"])
    
    st.sidebar.markdown(f"""
    <div style="background:rgba(8,13,26,0.6);border:1px solid rgba(148,163,184,0.1);
                border-radius:8px;padding:12px;margin-bottom:20px;">
        <div style="font-size:14px;font-weight:700;color:#E8F0FF;">{user['username']}</div>
        <div style="display:inline-block;background:{role_info['color']}18;
                    border:1px solid {role_info['color']}44;color:{role_info['color']};
                    font-size:10px;font-weight:700;letter-spacing:0.05em;
                    padding:2px 8px;border-radius:100px;margin-top:4px;">
            {role_info['icon']} {role_info['label']}
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if st.sidebar.button("Logout", use_container_width=True):
        import time
        st.session_state.user = None
        st.sidebar.success("Logged out")
        time.sleep(0.5)
        st.switch_page("Home.py")

"""
Streamlit auth guard — real RBAC enforcement.

This module performs an actual authentication + authorization check, instead of
auto-logging every user in as admin. It expects the user to have authenticated
through the login page (which sets `st.session_state.user`). If no user is
present, the page halts with a login prompt. If the user's role lacks the
required permission, the page halts with an access-denied message.
"""
import streamlit as st

from src.auth import has_permission, ROLES


def require_auth(permission: str = None) -> None:
    """
    Enforce authentication and (optionally) authorization.

    - If no user is in session_state, stop the page and ask the visitor to log in.
    - If `permission` is provided and the user's role lacks it, stop the page
      with an access-denied panel.

    The role string in session_state is normalized to match the keys of the
    `ROLES` dict (which are capitalized like "Admin", "Fraud_Analyst", etc.).
    """
    if "user" not in st.session_state or not st.session_state.user:
        st.warning("Please log in to access this page.")
        st.stop()

    user = st.session_state.user
    role = user.get("role")

    # Normalize role string to match ROLES keys (case-insensitive lookup)
    if role and role not in ROLES:
        for key in ROLES:
            if key.lower() == str(role).lower():
                user["role"] = key
                role = key
                break

    if permission is not None:
        if not role or not has_permission(role, permission):
            st.error(
                f"Access Denied: your role ({role or 'unknown'}) lacks the "
                f"required permission `{permission}`."
            )
            st.stop()


def display_user_profile():
    """Render the signed-in user's profile card in the sidebar."""
    if "user" not in st.session_state or not st.session_state.user:
        st.warning("Not logged in.")
        return

    user = st.session_state.user
    role = user.get("role", "Viewer")
    role_info = ROLES.get(role, ROLES.get("Viewer", {}))
    label = role_info.get("label", role)
    color = role_info.get("color", "#8899AA")

    st.sidebar.markdown(f"""
    <div style="background:#ffffff;border:1px solid #E2E8F0;
                border-radius:8px;padding:12px;margin-bottom:20px;
                box-shadow: 0 1px 2px rgba(0,0,0,0.05);">
        <div style="font-size:14px;font-weight:700;color:#0F172A;">{user.get('username', 'user')}</div>
        <div style="display:inline-block;background:#EFF6FF;
                    border:1px solid {color}33;color:{color};
                    font-size:10px;font-weight:700;letter-spacing:0.05em;
                    padding:2px 8px;border-radius:100px;margin-top:4px;">
            {label}
        </div>
    </div>
    """, unsafe_allow_html=True)

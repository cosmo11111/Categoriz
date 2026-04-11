import streamlit as st
from auth import get_supabase, is_logged_in, AUTH_CSS

st.set_page_config(page_title="Reset Password — Expense AI", page_icon="💳", layout="centered")
st.markdown(AUTH_CSS, unsafe_allow_html=True)

if is_logged_in():
    st.switch_page("app.py")

# ── Two modes: request reset OR set new password (arrived via email link) ─────
# Supabase sends a link like: https://yourapp.com/reset_password#access_token=...
# Streamlit can't read URL fragments directly, so we show the new-password form
# whenever the user lands on this page after a reset — the Supabase JS SDK would
# normally handle this, but in pure Python we check for a token in query params.
# Supabase can be configured to send PKCE links which append ?code= instead.
params = st.query_params

mode = "set_new" if "code" in params else "request"

if mode == "request":
    st.markdown("""
    <div class="auth-card">
      <div class="auth-logo">🔑</div>
      <div class="auth-title">Reset your password</div>
      <div class="auth-subtitle">We'll send a reset link to your email</div>
    </div>
    """, unsafe_allow_html=True)

    _, col, _ = st.columns([1, 2, 1])
    with col:
        msg_placeholder = st.empty()
        email = st.text_input("Email address", placeholder="you@example.com")

        if st.button("Send reset link", type="primary"):
            if not email.strip():
                msg_placeholder.markdown(
                    '<div class="auth-error">Please enter your email address.</div>',
                    unsafe_allow_html=True,
                )
            else:
                try:
                    sb = get_supabase()
                    sb.auth.reset_password_email(
                        email.strip(),
                        options={"redirect_to": f"{st.secrets.get('APP_URL', '')}/reset_password"},
                    )
                    # Always show success (prevents email enumeration)
                    msg_placeholder.markdown(
                        '<div class="auth-success">'
                        '✅ If that email is registered, you\'ll receive a reset link shortly. '
                        'Check your spam folder too.'
                        '</div>',
                        unsafe_allow_html=True,
                    )
                except Exception as e:
                    msg_placeholder.markdown(
                        f'<div class="auth-error">Something went wrong: {e}</div>',
                        unsafe_allow_html=True,
                    )

        st.markdown('<hr class="auth-divider">', unsafe_allow_html=True)
        st.markdown(
            '<div class="auth-link">Remembered it? '
            '<a href="/login" target="_self">Back to sign in</a></div>',
            unsafe_allow_html=True,
        )

else:
    # User arrived via the reset link — exchange code for session, then set new password
    st.markdown("""
    <div class="auth-card">
      <div class="auth-logo">🔑</div>
      <div class="auth-title">Set a new password</div>
      <div class="auth-subtitle">Choose a strong password for your account</div>
    </div>
    """, unsafe_allow_html=True)

    _, col, _ = st.columns([1, 2, 1])
    with col:
        msg_placeholder = st.empty()
        new_password = st.text_input("New password", type="password",
                                     placeholder="At least 8 characters")
        confirm      = st.text_input("Confirm password", type="password",
                                     placeholder="••••••••")

        if st.button("Update password", type="primary"):
            if len(new_password) < 8:
                msg_placeholder.markdown(
                    '<div class="auth-error">Password must be at least 8 characters.</div>',
                    unsafe_allow_html=True,
                )
            elif new_password != confirm:
                msg_placeholder.markdown(
                    '<div class="auth-error">Passwords do not match.</div>',
                    unsafe_allow_html=True,
                )
            else:
                try:
                    sb = get_supabase()
                    # Exchange the PKCE code for a session first
                    code = params["code"]
                    sb.auth.exchange_code_for_session({"auth_code": code})
                    # Now update the password
                    sb.auth.update_user({"password": new_password})
                    msg_placeholder.markdown(
                        '<div class="auth-success">'
                        '✅ Password updated! '
                        '<a href="/login" target="_self" style="color:#34d399">Sign in</a>'
                        '</div>',
                        unsafe_allow_html=True,
                    )
                    # Clear the code from URL
                    st.query_params.clear()
                except Exception as e:
                    msg_placeholder.markdown(
                        f'<div class="auth-error">Could not update password: {e}<br>'
                        'The reset link may have expired — '
                        '<a href="/reset_password" target="_self" style="color:#f87171">'
                        'request a new one</a>.</div>',
                        unsafe_allow_html=True,
                    )

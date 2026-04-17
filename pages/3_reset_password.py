import streamlit as st
from auth import get_supabase, is_logged_in, AUTH_CSS

st.set_page_config(page_title="Reset Password — Categoriz", page_icon="💳", layout="centered")
st.markdown(AUTH_CSS, unsafe_allow_html=True)
st.markdown("""
<style>
div[data-testid="stFormSubmitButton"] button {
    background-color: #f0c040 !important;
    color: #0f0f13 !important;
    border: none !important;
    font-weight: 600 !important;
    width: 100% !important;
}
[data-testid="InputInstructions"] { display: none !important; }
</style>""", unsafe_allow_html=True)

if is_logged_in():
    st.switch_page("frontend.py")

params = st.query_params

has_code  = "code"  in params
has_token = "token" in params
is_recovery = params.get("type") == "recovery"

mode = "set_new" if (has_code or has_token or is_recovery) else "request"

WORDMARK = """<div style="text-align:center;padding:48px 0 24px">
  <div style="font-family:'DM Sans',sans-serif;font-size:2.4rem;font-weight:700;
              font-style:italic;color:#f0c040;letter-spacing:.04em;margin-bottom:8px">
    CATEGORIZ
  </div>"""

# ── Request mode ──────────────────────────────────────────────────────────────
if mode == "request":
    st.markdown(WORDMARK + """
  <div style="font-size:1.1rem;font-weight:500;color:#e8e6e1;margin-bottom:4px">
    Reset your password
  </div>
  <div style="font-size:.85rem;color:#666">We'll send a reset link to your email</div>
</div>""", unsafe_allow_html=True)

    _, col, _ = st.columns([1, 2, 1])
    with col:
        msg = st.empty()
        email = st.text_input("Email address", placeholder="you@example.com")
        if st.button("Send reset link", type="primary"):
            if not email.strip():
                msg.markdown('<div class="auth-error">Please enter your email address.</div>',
                             unsafe_allow_html=True)
            else:
                try:
                    sb  = get_supabase()
                    app = st.secrets.get("APP_URL", "").rstrip("/")
                    sb.auth.reset_password_email(
                        email.strip(),
                        options={"redirect_to": f"{app}/reset_password"},
                    )
                    msg.markdown(
                        '<div class="auth-success">✅ If that email is registered, '
                        "you'll receive a reset link shortly. Check your spam folder too.</div>",
                        unsafe_allow_html=True,
                    )
                except Exception as e:
                    msg.markdown(f'<div class="auth-error">Something went wrong: {e}</div>',
                                 unsafe_allow_html=True)

        st.markdown('<hr class="auth-divider">', unsafe_allow_html=True)
        st.markdown('<div class="auth-link">Remembered it? '
                    '<a href="/1_login" target="_self">Back to sign in</a></div>',
                    unsafe_allow_html=True)

# ── Set new password mode ─────────────────────────────────────────────────────
else:
    st.markdown(WORDMARK + """
  <div style="font-size:1.1rem;font-weight:500;color:#e8e6e1;margin-bottom:4px">
    Set a new password
  </div>
  <div style="font-size:.85rem;color:#666">Choose a strong password for your account</div>
</div>""", unsafe_allow_html=True)

    # Exchange the code/token for a session exactly once per page load.
    # Store the result in session_state so Streamlit reruns don't re-consume it.
    if "reset_session_verified" not in st.session_state:
        sb = get_supabase()
        verified = False
        debug_info = {"has_code": has_code, "has_token": has_token,
                      "is_recovery": is_recovery, "params": dict(params)}

        # PKCE flow — ?code=...
        if has_code:
            try:
                sb.auth.exchange_code_for_session({"auth_code": params["code"]})
                verified = True
                debug_info["method"] = "exchange_code_for_session: OK"
            except Exception as ex:
                debug_info["method"] = f"exchange_code_for_session: FAILED — {ex}"

        # Legacy OTP flow — ?token=...&type=recovery&email=...
        if not verified and has_token and is_recovery:
            email_param = params.get("email", "")
            if not email_param:
                # Email missing from URL — store token, ask user for email
                # Don't set reset_session_verified yet — wait for email entry
                st.session_state.reset_token      = params["token"]
                st.session_state.reset_needs_email = True
                debug_info["method"] = "verify_otp: needs email from user"
                st.session_state.reset_debug = debug_info
                # Skip setting reset_session_verified — let the email form handle it
            else:
                try:
                    sb.auth.verify_otp({
                        "email": email_param,
                        "token": params["token"],
                        "type":  "recovery",
                    })
                    verified = True
                    st.session_state.reset_email = email_param
                    debug_info["method"] = "verify_otp: OK"
                    st.session_state.reset_session_verified = verified
                    st.session_state.reset_debug = debug_info
                except Exception as ex:
                    debug_info["method"] = f"verify_otp: FAILED — {ex}"
                    st.session_state.reset_session_verified = False
                    st.session_state.reset_debug = debug_info
        else:
            st.session_state.reset_session_verified = verified
            st.session_state.reset_debug = debug_info

    _, col, _ = st.columns([1, 2, 1])
    with col:
        msg = st.empty()
        verified = st.session_state.get("reset_session_verified", False)

        # If token exists but we need the email, show email entry + verify form
        if not verified and st.session_state.get("reset_needs_email"):
            st.markdown(
                "<p style='color:#888;font-size:.85rem;margin-bottom:8px'>"
                "Enter your email address to confirm your identity.</p>",
                unsafe_allow_html=True,
            )
            with st.form("verify_email_form", border=False):
                email_input = st.text_input("Email address",
                                             placeholder="you@example.com")
                verify_submitted = st.form_submit_button("Continue",
                                                          use_container_width=True)
            if verify_submitted and email_input.strip():
                try:
                    sb.auth.verify_otp({
                        "email": email_input.strip(),
                        "token": st.session_state.reset_token,
                        "type":  "recovery",
                    })
                    st.session_state.reset_session_verified = True
                    st.session_state.reset_email = email_input.strip()
                    st.session_state.reset_needs_email = False
                    st.rerun()
                except Exception as ex:
                    msg.markdown(
                        f'<div class="auth-error">Could not verify: {ex}<br>'
                        'The link may have expired — '
                        '<a href="/3_reset_password" target="_self" style="color:#f87171">'
                        'request a new one</a>.</div>',
                        unsafe_allow_html=True,
                    )
            st.stop()

        if not verified:
            st.markdown(
                '<div class="auth-error" style="margin-bottom:16px">'
                '⚠️ This reset link has expired or is invalid. '
                '<a href="/3_reset_password" target="_self" style="color:#f87171">'
                'Request a new one</a>.</div>',
                unsafe_allow_html=True,
            )
            st.stop()

        saved_email = st.session_state.get("reset_email", "")
        if saved_email:
            st.markdown(
                f"<p style='color:#888;font-size:.85rem;margin-bottom:8px'>"
                f"Resetting password for <b style='color:#e8e6e1'>{saved_email}</b></p>",
                unsafe_allow_html=True,
            )

        with st.form("reset_form", border=False):
            new_password = st.text_input("New password", type="password",
                                         placeholder="At least 8 characters")
            confirm      = st.text_input("Confirm password", type="password",
                                         placeholder="••••••••")
            submitted    = st.form_submit_button("Update password",
                                                  use_container_width=True)

        if submitted:
            if len(new_password) < 8:
                msg.markdown(
                    '<div class="auth-error">Password must be at least 8 characters.</div>',
                    unsafe_allow_html=True)
            elif new_password != confirm:
                msg.markdown(
                    '<div class="auth-error">Passwords do not match.</div>',
                    unsafe_allow_html=True)
            else:
                try:
                    sb = get_supabase()
                    sb.auth.update_user({"password": new_password})
                    msg.markdown(
                        '<div class="auth-success">✅ Password updated! '
                        '<a href="/1_login" target="_self" style="color:#34d399">'
                        'Sign in</a></div>',
                        unsafe_allow_html=True,
                    )
                    st.query_params.clear()
                    st.session_state.pop("reset_session_verified", None)
                    st.session_state.pop("reset_email", None)
                except Exception as e:
                    msg.markdown(
                        f'<div class="auth-error">Could not update password: {e}<br>'
                        'The session may have expired — '
                        '<a href="/3_reset_password" target="_self" style="color:#f87171">'
                        'request a new link</a>.</div>',
                        unsafe_allow_html=True,
                    )

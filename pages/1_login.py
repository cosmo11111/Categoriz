import streamlit as st
from auth import get_supabase, set_session, is_logged_in, AUTH_CSS

st.set_page_config(page_title="Login — Expense AI", page_icon="💳", layout="centered")
st.markdown(AUTH_CSS, unsafe_allow_html=True)

# Already logged in → go straight to app
if is_logged_in():
    st.switch_page("frontend.py")

st.markdown("""
<div style="text-align:center;padding:48px 0 24px">
  <div style="font-family:'DM Sans',sans-serif;font-size:2.4rem;font-weight:700;
              font-style:italic;color:#f0c040;letter-spacing:.04em;margin-bottom:8px">
    CATEGORIZ
  </div>
  <div style="font-size:1.1rem;font-weight:500;color:#e8e6e1;margin-bottom:4px">
    Welcome back
  </div>
  <div style="font-size:.85rem;color:#666">
    Sign in to your Categoriz account
  </div>
</div>
""", unsafe_allow_html=True)

# Centre the form using columns
_, col, _ = st.columns([1, 2, 1])

with col:
    msg_placeholder = st.empty()

    email    = st.text_input("Email address", placeholder="you@example.com",
                              key="login_email", label_visibility="visible")
    password = st.text_input("Password", type="password", placeholder="••••••••",
                              key="login_password", label_visibility="visible")
    signin   = st.button("Sign in", type="primary", use_container_width=True,
                          key="login_btn")

    # Wire Enter key to Sign in button and hide the hint text
    import streamlit.components.v1 as _c
    _c.html("""
<script>
(function() {
  // Inject a script tag into the parent document so it runs in the main page
  // context — not the sandboxed iframe context
  var s = window.parent.document.createElement('script');
  s.textContent = `
    (function() {
      if (window._loginEnterRegistered) return;
      window._loginEnterRegistered = true;
      document.addEventListener('keydown', function(e) {
        if (e.key !== 'Enter') return;
        var tag = e.target.tagName.toLowerCase();
        if (tag !== 'input') return;
        var btn = document.querySelector('button[data-testid="baseButton-primary"]');
        if (btn) { e.preventDefault(); btn.click(); }
      });
    })();
  `;
  window.parent.document.head.appendChild(s);

  // Also hide the "Press Enter to submit" hint via parent CSS
  var style = window.parent.document.createElement('style');
  style.textContent = '[data-testid="InputInstructions"] { display:none !important; }';
  window.parent.document.head.appendChild(style);
})();
</script>
""", height=0)

    if signin:
        if not email or not password:
            msg_placeholder.markdown(
                '<div class="auth-error">Please enter your email and password.</div>',
                unsafe_allow_html=True,
            )
        else:
            try:
                sb = get_supabase()
                res = sb.auth.sign_in_with_password(
                    {"email": email.strip(), "password": password}
                )
                set_session({"user": res.user, "access_token": res.session.access_token})
                st.switch_page("frontend.py")
            except Exception as e:
                err = str(e)
                if "Invalid login" in err or "invalid" in err.lower():
                    msg = "Incorrect email or password."
                elif "Email not confirmed" in err:
                    msg = "Please confirm your email before signing in."
                else:
                    msg = f"Sign-in failed: {err}"
                msg_placeholder.markdown(
                    f'<div class="auth-error">{msg}</div>',
                    unsafe_allow_html=True,
                )

    st.markdown('<hr class="auth-divider">', unsafe_allow_html=True)

    st.markdown(
        '<div class="auth-link">Forgot your password? '
        '<a href="/reset_password" target="_self">Reset it</a></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="auth-link" style="margin-top:8px">No account? '
        '<a href="/signup" target="_self">Sign up free</a></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="auth-link" style="margin-top:16px;font-size:.75rem;color:#444">'
        '<a href="https://drive.google.com/file/d/1Yl0ed8IiMzYalV2rcXUsLtBymnvvjyZ5/view?usp=sharing" target="_blank" style="color:#555">📄 Privacy Policy</a>'
        '</div>',
        unsafe_allow_html=True,
    )

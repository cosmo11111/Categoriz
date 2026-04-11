import streamlit as st
import streamlit.components.v1 as components
from auth import require_auth, get_user, clear_session, get_supabase
from db import load_reports, load_report_items, delete_report, DEFAULT_CATEGORY_COLORS

st.set_page_config(page_title="Saved Reports — Expense AI", page_icon="💳", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;500;600&display=swap');
html, body, .stApp { font-family:'DM Sans',sans-serif; background:#0f0f13; color:#e8e6e1; }
section[data-testid="stSidebar"] { background:#17171d !important; border-right:1px solid #2a2a35; }
section[data-testid="stSidebar"] * { color:#c9c7c0 !important; }
#MainMenu { visibility:hidden; } footer { visibility:hidden; }
.stButton button { border-radius:8px !important; font-weight:500 !important; transition:all .15s !important; }
.stButton button[kind="primary"] { background:#f0c040 !important; color:#0f0f13 !important; border:none !important; }
/* Make delete buttons look danger-ish */
div[data-testid="stHorizontalBlock"] .stButton button {
    font-size:12px !important; padding:4px 12px !important;
}
</style>
""", unsafe_allow_html=True)

require_auth()

user  = get_user()
uid   = user.id if hasattr(user, "id") else user.get("id") if user else None
email = user.email if hasattr(user, "email") else user.get("email","") if user else ""

with st.sidebar:
    st.markdown("## 💳 Expense AI")
    st.markdown("---")
    st.markdown(f"<p style='color:#888;font-size:.8rem;margin-bottom:4px'>Signed in as</p>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:#e8e6e1;font-size:.85rem;font-weight:500;word-break:break-all'>{email}</p>", unsafe_allow_html=True)
    st.markdown("---")
    if st.button("← Back to app", use_container_width=True):
        st.switch_page("frontend.py")
    if st.button("Sign out", use_container_width=True):
        try:
            get_supabase().auth.sign_out()
        except Exception:
            pass
        clear_session()
        st.switch_page("pages/1_login.py")

if not uid:
    st.warning("Please sign in to view saved reports.")
    st.stop()

reports = load_reports(uid)

col_title, col_btn = st.columns([4, 1])
with col_title:
    st.markdown("## 📂 Saved Reports")
    if reports:
        st.caption(f"{len(reports)} report{'s' if len(reports)!=1 else ''}")
with col_btn:
    if st.button("＋ New analysis", type="primary", use_container_width=True):
        st.switch_page("frontend.py")

st.markdown("---")

if not reports:
    st.markdown("""
    <div style="text-align:center;padding:4rem 1rem">
        <div style="font-size:2.5rem;margin-bottom:16px">📂</div>
        <p style="font-size:1.1rem;color:#e8e6e1;margin-bottom:8px">No saved reports yet</p>
        <p style="color:#666;font-size:.9rem">Upload a bank statement, categorize your expenses,<br>then save the report from Step 3.</p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

CATEGORY_COLORS = DEFAULT_CATEGORY_COLORS

def cat_pill(cat):
    color = CATEGORY_COLORS.get(cat, "#6b7280")
    return (f'<span style="display:inline-block;padding:2px 9px;border-radius:20px;'
            f'font-size:11px;background:{color}22;color:{color};border:1px solid {color}44">'
            f'{cat}</span>')

def format_amount(v):
    sign = "−" if v < 0 else "+"
    return f"{sign}${abs(v):,.2f}"

def amount_color(v):
    return "#f87171" if v < 0 else "#34d399"

# ── Handle pending delete from callback ────────────────────────────────────────
if "pending_delete_report" in st.session_state:
    rid_to_delete = st.session_state.pop("pending_delete_report")
    ok, err = delete_report(rid_to_delete)
    if ok:
        st.toast("Report deleted", icon="🗑️")
    else:
        st.toast(f"Could not delete: {err}", icon="⚠️")
    st.rerun()

# ── Render each report ─────────────────────────────────────────────────────────
for report in reports:
    rid          = report["id"]
    label        = report["label"]
    period_start = report.get("period_start") or ""
    period_end   = report.get("period_end") or ""
    total_spend  = float(report.get("total_spend") or 0)
    total_income = float(report.get("total_income") or 0)
    created_at   = (report.get("created_at") or "")[:10]
    net          = total_income + total_spend
    net_color    = "#34d399" if net >= 0 else "#f87171"
    net_sign     = "+" if net >= 0 else "−"

    period_str = ""
    if period_start and period_end:
        period_str = f"{period_start} – {period_end} · "
    elif period_start:
        period_str = f"From {period_start} · "

    items = load_report_items(rid)
    n_tx  = len(items)

    # Build transaction rows HTML
    tx_rows_html = ""
    for item in items:
        vendor  = item.get("vendor_name") or ""
        is_red  = item.get("is_redacted", False)
        amt     = float(item.get("amount") or 0)
        cat     = item.get("category","Unknown")
        date    = item.get("date","")
        vendor_cell = (
            '<span style="color:#444;font-style:italic">⬛ redacted</span>'
            if is_red else vendor
        )
        tx_rows_html += f"""<tr>
            <td>{date}</td>
            <td>{vendor_cell}</td>
            <td style="color:{amount_color(amt)};font-family:\'DM Mono\',monospace">{format_amount(amt)}</td>
            <td>{cat_pill(cat)}</td>
        </tr>"""

    # ── Self-contained card HTML (no parent communication needed) ─────────────
    # The card starts COLLAPSED (header only = 70px).
    # JS toggles an internal open/close; we measure content height after open
    # and resize the iframe via postMessage so Streamlit expands it.
    card_html = f"""<!DOCTYPE html><html><head>
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;500;600&display=swap');
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'DM Sans',sans-serif;background:transparent;overflow:hidden}}
.card{{background:#1a1a24;border:1px solid #2a2a38;border-radius:12px;overflow:hidden}}
.hdr{{display:flex;justify-content:space-between;align-items:center;padding:16px 20px;cursor:pointer;user-select:none;transition:background .15s}}
.hdr:hover{{background:#1e1e2e}}
.lbl{{font-size:15px;font-weight:500;color:#e8e6e1}}
.meta{{font-size:12px;color:#555;margin-top:3px}}
.stats{{display:flex;gap:24px;align-items:center}}
.stat{{text-align:right}}
.sv{{font-size:14px;font-weight:500;font-family:'DM Mono',monospace}}
.sl{{font-size:10px;color:#555;margin-top:1px;text-transform:uppercase;letter-spacing:.04em}}
.chev{{color:#555;margin-left:14px;font-size:11px;transition:transform .2s;display:inline-block}}
.chev.open{{transform:rotate(180deg)}}
.body{{display:none;border-top:1px solid #1e1e28;padding:16px 20px}}
.mgs{{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:16px}}
.mp{{background:#0f0f13;border-radius:8px;padding:10px 12px}}
.mv{{font-size:15px;font-weight:500;font-family:'DM Mono',monospace}}
.ml{{font-size:10px;color:#555;margin-top:3px;text-transform:uppercase;letter-spacing:.04em}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
th{{color:#555;font-weight:400;text-align:left;padding:6px 8px;border-bottom:1px solid #2a2a38;font-size:10px;text-transform:uppercase;letter-spacing:.06em}}
td{{padding:7px 8px;border-bottom:1px solid #1e1e28;color:#e8e6e1}}
tr:last-child td{{border-bottom:none}}
</style>
</head><body>
<div class="card" id="card">
  <div class="hdr" onclick="toggle()">
    <div>
      <div class="lbl">{label}</div>
      <div class="meta">{period_str}saved {created_at}</div>
    </div>
    <div style="display:flex;align-items:center">
      <div class="stats">
        <div class="stat">
          <div class="sv" style="color:#f87171">${abs(total_spend):,.2f}</div>
          <div class="sl">spent</div>
        </div>
        <div class="stat">
          <div class="sv" style="color:#34d399">${total_income:,.2f}</div>
          <div class="sl">income</div>
        </div>
        <div class="stat">
          <div class="sv" style="color:#e8e6e1">{n_tx}</div>
          <div class="sl">transactions</div>
        </div>
      </div>
      <span class="chev" id="chev">▼</span>
    </div>
  </div>
  <div class="body" id="body">
    <div class="mgs">
      <div class="mp"><div class="mv" style="color:#f87171">${abs(total_spend):,.2f}</div><div class="ml">Total spent</div></div>
      <div class="mp"><div class="mv" style="color:#34d399">${total_income:,.2f}</div><div class="ml">Income</div></div>
      <div class="mp"><div class="mv" style="color:{net_color}">{net_sign}${abs(net):,.2f}</div><div class="ml">Net</div></div>
      <div class="mp"><div class="mv" style="color:#e8e6e1">{n_tx}</div><div class="ml">Transactions</div></div>
    </div>
    <table>
      <thead><tr><th style="width:12%">Date</th><th style="width:36%">Merchant</th><th style="width:15%">Amount</th><th>Category</th></tr></thead>
      <tbody>{tx_rows_html}</tbody>
    </table>
  </div>
</div>
<script>
var open = false;
function toggle() {{
  open = !open;
  document.getElementById('body').style.display = open ? 'block' : 'none';
  document.getElementById('chev').classList.toggle('open', open);
  // Tell Streamlit the new height needed
  var h = document.getElementById('card').scrollHeight + 4;
  window.parent.postMessage({{type:'streamlit:setFrameHeight', height: h}}, '*');
}}
// Start at collapsed header height
window.parent.postMessage({{type:'streamlit:setFrameHeight', height: 72}}, '*');
</script>
</body></html>"""

    # Render card — start collapsed at 72px, JS expands via setFrameHeight
    components.html(card_html, height=72, scrolling=False)

    # ── Delete button rendered natively in Streamlit (reliable) ───────────────
    _, del_col = st.columns([5, 1])
    with del_col:
        def _make_delete_cb(report_id):
            def _cb():
                st.session_state.pending_delete_report = report_id
            return _cb

        st.button(
            "🗑 Delete",
            key=f"del_report_{rid}",
            on_click=_make_delete_cb(rid),
            use_container_width=True,
        )

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

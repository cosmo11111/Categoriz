import streamlit as st
import fitz  # PyMuPDF
import pdfplumber
import io
import base64
import json
import plotly.graph_objects as go

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="PDF Highlighter", page_icon="🖊️", layout="wide")

st.markdown("""
<style>
  .stApp { background-color: #f5f5f0; }
  .info-box {
    background:#fffbea; border-left:4px solid #f0c040;
    padding:.75rem 1rem; border-radius:4px;
    font-size:.88rem; color:#555; margin-bottom:.5rem;
  }
  .stat-box {
    background:white; border-radius:8px; padding:.75rem 1rem;
    box-shadow:0 1px 3px rgba(0,0,0,.08); text-align:center;
  }
</style>
""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────
COLORS_RGB = {
    "Yellow": (1, 1, 0),      "Green":  (0, 1, 0.4),
    "Cyan":   (0, 0.9, 1),    "Pink":   (1, 0.4, 0.7),
    "Orange": (1, 0.6, 0),
}
COLORS_RGBA = {
    "Yellow": "rgba(255,255,0,0.35)",    "Green":  "rgba(0,255,100,0.35)",
    "Cyan":   "rgba(0,220,255,0.35)",    "Pink":   "rgba(255,100,180,0.35)",
    "Orange": "rgba(255,153,0,0.35)",
}
COLORS_LINE = {
    "Yellow": "rgba(200,180,0,0.8)",     "Green":  "rgba(0,180,80,0.8)",
    "Cyan":   "rgba(0,180,220,0.8)",     "Pink":   "rgba(220,60,150,0.8)",
    "Orange": "rgba(220,120,0,0.8)",
}

# ── Session state ─────────────────────────────────────────────────────────────
for k, v in [("page_num", 0), ("highlights", {}), ("pdf_bytes", None), ("zoom", 1.5)]:
    if k not in st.session_state:
        st.session_state[k] = v

# ── Helpers ───────────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def render_page_b64(pdf_bytes: bytes, page_num: int, zoom: float):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pix = doc[page_num].get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
    doc.close()
    b64 = base64.b64encode(pix.tobytes("png")).decode()
    return b64, pix.width, pix.height


def snap_to_words(pdf_bytes, page_num, rect):
    x0, y0, x1, y1 = rect
    hits = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for w in (pdf.pages[page_num].extract_words() or []):
            if w["x0"] < x1 and w["x1"] > x0 and w["top"] < y1 and w["bottom"] > y0:
                hits.append((w["x0"], w["top"], w["x1"], w["bottom"]))
    if not hits:
        return rect
    return (min(h[0] for h in hits), min(h[1] for h in hits),
            max(h[2] for h in hits), max(h[3] for h in hits))


def build_pdf(original_bytes, highlights):
    doc = fitz.open(stream=original_bytes, filetype="pdf")
    for pn, hl_list in highlights.items():
        page = doc[int(pn)]
        for h in hl_list:
            annot = page.add_highlight_annot(fitz.Rect(*h["rect"]))
            annot.set_colors(stroke=COLORS_RGB.get(h["color"], (1, 1, 0)))
            annot.update()
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


def make_figure(b64: str, img_w: int, img_h: int,
                saved_highlights: list, color: str) -> go.Figure:
    """
    Build a Plotly figure with the PDF page as background image.
    dragmode='drawrect' lets users draw rectangles natively.
    Saved highlights are drawn as filled shapes.
    """
    fig = go.Figure()

    # Invisible scatter so Plotly sets up axes properly
    fig.add_trace(go.Scatter(x=[0, img_w], y=[0, img_h],
                             mode="markers", marker=dict(opacity=0),
                             showlegend=False, hoverinfo="none"))

    # PDF page as background
    fig.add_layout_image(dict(
        source=f"data:image/png;base64,{b64}",
        xref="x", yref="y",
        x=0, y=img_h,
        sizex=img_w, sizey=img_h,
        sizing="stretch",
        layer="below",
    ))

    # Draw existing highlights as filled rectangles
    shapes = []
    for h in saved_highlights:
        x0, y0_pdf, x1, y1_pdf = h["rect"]
        # Plotly y-axis is flipped vs PDF (PDF: 0=top, Plotly: 0=bottom)
        shapes.append(dict(
            type="rect",
            xref="x", yref="y",
            x0=x0, x1=x1,
            y0=img_h - y1_pdf, y1=img_h - y0_pdf,
            fillcolor=COLORS_RGBA.get(h["color"], "rgba(255,255,0,0.35)"),
            line=dict(width=0),
            layer="above",
        ))

    fig.update_layout(
        width=img_w,
        height=img_h,
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(range=[0, img_w], showgrid=False, zeroline=False,
                   showticklabels=False, fixedrange=True),
        yaxis=dict(range=[0, img_h], showgrid=False, zeroline=False,
                   showticklabels=False, fixedrange=True, scaleanchor="x"),
        dragmode="drawrect",
        newshape=dict(
            fillcolor=COLORS_RGBA[color],
            line=dict(color=COLORS_LINE[color], width=1),
        ),
        shapes=shapes,
        plot_bgcolor="white",
        paper_bgcolor="white",
    )

    return fig

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🖊️ PDF Highlighter")
    st.markdown("---")
    uploaded = st.file_uploader("Upload a PDF", type=["pdf"])
    if uploaded:
        b = uploaded.read()
        if b != st.session_state.pdf_bytes:
            st.session_state.pdf_bytes = b
            st.session_state.page_num = 0
            st.session_state.highlights = {}
            render_page_b64.clear()

    color = st.selectbox("Highlight colour", list(COLORS_RGB.keys()))
    zoom  = st.slider("Zoom", 1.0, 3.0, st.session_state.zoom, 0.25)
    if zoom != st.session_state.zoom:
        st.session_state.zoom = zoom
        render_page_b64.clear()
    snap = st.toggle("Snap to word boundaries", value=True)

    st.markdown("---")
    total_h = sum(len(v) for v in st.session_state.highlights.values())
    if total_h:
        st.caption(f"{total_h} highlight{'s' if total_h != 1 else ''} total")
    if st.button("🗑️ Clear all highlights", use_container_width=True):
        st.session_state.highlights = {}
        st.rerun()

# ── Main ──────────────────────────────────────────────────────────────────────
st.markdown("## 🖊️ PDF Highlighter")
st.caption("Upload a PDF · drag to draw a rectangle · click **Add Highlight** · download")

if not st.session_state.pdf_bytes:
    st.markdown('<div class="info-box">👆 Upload a PDF in the sidebar to begin.</div>',
                unsafe_allow_html=True)
    st.stop()

pdf_bytes = st.session_state.pdf_bytes
doc_tmp   = fitz.open(stream=pdf_bytes, filetype="pdf")
n_pages   = len(doc_tmp); doc_tmp.close()

# Page navigation
c1, c2, c3 = st.columns([1, 4, 1])
with c1:
    if st.button("◀ Prev", use_container_width=True,
                 disabled=st.session_state.page_num == 0):
        st.session_state.page_num -= 1; st.rerun()
with c2:
    st.markdown(f"<p style='text-align:center;margin:6px 0;font-weight:600'>"
                f"Page {st.session_state.page_num + 1} of {n_pages}</p>",
                unsafe_allow_html=True)
with c3:
    if st.button("Next ▶", use_container_width=True,
                 disabled=st.session_state.page_num == n_pages - 1):
        st.session_state.page_num += 1; st.rerun()

pn = st.session_state.page_num
zm = st.session_state.zoom
b64, img_w, img_h = render_page_b64(pdf_bytes, pn, zm)
pk = str(pn)
saved_hl = st.session_state.highlights.get(pk, [])

st.markdown(
    '<div class="info-box">'
    '🖱️ <b>Click and drag</b> on the PDF to draw a yellow box. '
    'Then click <b>Add Highlight</b> to save it. '
    'Use the toolbar top-right of the chart to zoom/pan/reset.'
    '</div>',
    unsafe_allow_html=True,
)

fig = make_figure(b64, img_w, img_h, saved_hl, color)

# st.plotly_chart with on_select captures drawn shapes
event_data = st.plotly_chart(
    fig,
    use_container_width=False,
    key=f"chart_{pn}_{zm}",
    on_select="rerun",   # rerun when user draws/selects
    selection_mode=["box"],
)

# ── Parse the newly drawn shape ───────────────────────────────────────────────
# Plotly returns drawn shapes via event_data.selection.box (Streamlit ≥1.33)
# and also via the relayout event captured in the figure's shapes list.
new_rect = None

# Method 1: relayout shapes (most reliable) — Plotly appends drawn rects
# to fig.layout.shapes; Streamlit exposes these via the chart's return value.
try:
    sel = event_data.selection  # type: ignore
    # Drawn rectangles show up in sel.box as [{x, y}] pairs
    boxes = getattr(sel, "box", []) or []
    if boxes:
        box = boxes[-1]  # take the most recent
        xs = box.get("x", [])
        ys = box.get("y", [])
        if len(xs) >= 2 and len(ys) >= 2:
            # Plotly coords: y is in Plotly space (0=bottom), convert to PDF space (0=top)
            cx0, cx1 = min(xs), max(xs)
            py_lo, py_hi = min(ys), max(ys)
            # PDF y: 0 at top → invert
            pdf_y0 = img_h - py_hi
            pdf_y1 = img_h - py_lo
            new_rect = (cx0, pdf_y0, cx1, pdf_y1)
except Exception:
    pass

# ── Action buttons ────────────────────────────────────────────────────────────
b1, b2 = st.columns(2)
with b1:
    if st.button("✅ Add Highlight", use_container_width=True, type="primary"):
        if new_rect is None:
            st.warning("Draw a rectangle on the PDF first, then click Add Highlight.")
        else:
            x0, y0, x1, y1 = new_rect
            # Convert from canvas pixels → PDF points (undo zoom)
            px0, py0, px1, py1 = x0/zm, y0/zm, x1/zm, y1/zm
            if snap:
                px0, py0, px1, py1 = snap_to_words(pdf_bytes, pn, (px0, py0, px1, py1))
            st.session_state.highlights.setdefault(pk, []).append(
                {"rect": [px0, py0, px1, py1], "color": color}
            )
            st.rerun()

with b2:
    if st.button("↩️ Undo last highlight", use_container_width=True):
        if st.session_state.highlights.get(pk):
            st.session_state.highlights[pk].pop()
            if not st.session_state.highlights[pk]:
                del st.session_state.highlights[pk]
            st.rerun()

# ── Download ──────────────────────────────────────────────────────────────────
st.markdown("---")
total = sum(len(v) for v in st.session_state.highlights.values())
dc, sc = st.columns([3, 1])
with sc:
    st.markdown(
        f"<div class='stat-box'><b style='font-size:1.5rem'>{total}</b><br>"
        f"<span style='font-size:.8rem;color:#888'>highlight{'s' if total!=1 else ''}</span></div>",
        unsafe_allow_html=True,
    )
with dc:
    if total > 0:
        st.download_button(
            "⬇️ Download highlighted PDF",
            data=build_pdf(pdf_bytes, st.session_state.highlights),
            file_name="highlighted.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    else:
        st.info("Add highlights above, then download here.")

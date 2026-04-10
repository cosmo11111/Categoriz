import streamlit as st
import fitz  # PyMuPDF
import pdfplumber
import io
import json
from PIL import Image
from streamlit_drawable_canvas import st_canvas

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="PDF Highlighter",
    page_icon="🖊️",
    layout="wide",
)

# ── Styling ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .stApp { background-color: #f5f5f0; }
    .main-title {
        font-size: 2rem; font-weight: 700; color: #1a1a2e;
        margin-bottom: 0; padding-bottom: 0;
    }
    .subtitle {
        font-size: 0.95rem; color: #555; margin-top: 0;
        margin-bottom: 1.5rem;
    }
    .info-box {
        background: #fffbea; border-left: 4px solid #f0c040;
        padding: 0.75rem 1rem; border-radius: 4px;
        font-size: 0.88rem; color: #555; margin-bottom: 1rem;
    }
    .stat-box {
        background: white; border-radius: 8px; padding: 0.75rem 1rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08); text-align: center;
    }
    div[data-testid="stSidebarContent"] { background-color: #1a1a2e; }
    div[data-testid="stSidebarContent"] * { color: white !important; }
    div[data-testid="stSidebarContent"] .stSelectbox label,
    div[data-testid="stSidebarContent"] .stSlider label { color: #ccc !important; }
</style>
""", unsafe_allow_html=True)

# ── Session state defaults ────────────────────────────────────────────────────
for key, default in [
    ("page_num", 0),
    ("highlights", {}),   # {page_num: [{"rect": [...], "color": str}]}
    ("pdf_bytes", None),
    ("zoom", 1.5),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── Helpers ───────────────────────────────────────────────────────────────────
HIGHLIGHT_COLORS = {
    "Yellow":  (1, 1, 0),
    "Green":   (0, 1, 0.4),
    "Cyan":    (0, 0.9, 1),
    "Pink":    (1, 0.4, 0.7),
    "Orange":  (1, 0.6, 0),
}

CANVAS_COLORS = {
    "Yellow":  "rgba(255, 255,   0, 0.35)",
    "Green":   "rgba(  0, 255, 100, 0.35)",
    "Cyan":    "rgba(  0, 230, 255, 0.35)",
    "Pink":    "rgba(255, 100, 180, 0.35)",
    "Orange":  "rgba(255, 153,   0, 0.35)",
}


@st.cache_data(show_spinner=False)
def render_page(pdf_bytes: bytes, page_num: int, zoom: float) -> Image.Image:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc[page_num]
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    doc.close()
    return img


def snap_to_words(pdf_bytes: bytes, page_num: int, rect_pdf, zoom: float):
    """Expand a rect to snap to any overlapping words."""
    x0, y0, x1, y1 = rect_pdf
    snapped_words = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        page = pdf.pages[page_num]
        for word in (page.extract_words() or []):
            wx0, wy0, wx1, wy1 = word["x0"], word["top"], word["x1"], word["bottom"]
            # Check overlap
            if wx0 < x1 and wx1 > x0 and wy0 < y1 and wy1 > y0:
                snapped_words.append((wx0, wy0, wx1, wy1))
    if not snapped_words:
        return rect_pdf
    sx0 = min(w[0] for w in snapped_words)
    sy0 = min(w[1] for w in snapped_words)
    sx1 = max(w[2] for w in snapped_words)
    sy1 = max(w[3] for w in snapped_words)
    return (sx0, sy0, sx1, sy1)


def build_annotated_pdf(original_bytes: bytes, highlights: dict) -> bytes:
    doc = fitz.open(stream=original_bytes, filetype="pdf")
    for page_num, page_highlights in highlights.items():
        page = doc[int(page_num)]
        for h in page_highlights:
            rect = fitz.Rect(*h["rect"])
            color_rgb = HIGHLIGHT_COLORS.get(h["color"], (1, 1, 0))
            annot = page.add_highlight_annot(rect)
            annot.set_colors(stroke=color_rgb)
            annot.update()
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🖊️ PDF Highlighter")
    st.markdown("---")

    uploaded = st.file_uploader("Upload a PDF", type=["pdf"])
    if uploaded:
        new_bytes = uploaded.read()
        if new_bytes != st.session_state.pdf_bytes:
            st.session_state.pdf_bytes = new_bytes
            st.session_state.page_num = 0
            st.session_state.highlights = {}

    st.markdown("### Highlight colour")
    color_choice = st.selectbox(
        "Colour", list(HIGHLIGHT_COLORS.keys()), label_visibility="collapsed"
    )

    st.markdown("### Zoom")
    zoom = st.slider("Zoom", 1.0, 3.0, 1.5, 0.25, label_visibility="collapsed")
    if zoom != st.session_state.zoom:
        st.session_state.zoom = zoom
        render_page.clear()

    st.markdown("### Snap to words")
    snap = st.toggle("Snap selection to word boundaries", value=True)

    st.markdown("---")
    if st.session_state.highlights:
        total = sum(len(v) for v in st.session_state.highlights.values())
        st.markdown(f"**{total}** highlight{'s' if total != 1 else ''} added")

    if st.button("🗑️ Clear all highlights", use_container_width=True):
        st.session_state.highlights = {}
        st.rerun()

# ── Main area ─────────────────────────────────────────────────────────────────
st.markdown('<p class="main-title">PDF Highlighter</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="subtitle">Upload a PDF → drag to select text → highlights are saved to your download</p>',
    unsafe_allow_html=True,
)

if not st.session_state.pdf_bytes:
    st.markdown("""
    <div class="info-box">
        👆 Upload a PDF using the sidebar to get started.
    </div>
    """, unsafe_allow_html=True)
    st.stop()

pdf_bytes = st.session_state.pdf_bytes
doc_info = fitz.open(stream=pdf_bytes, filetype="pdf")
total_pages = len(doc_info)
doc_info.close()

# Page navigation
col1, col2, col3 = st.columns([1, 3, 1])
with col1:
    if st.button("◀ Prev", use_container_width=True, disabled=st.session_state.page_num == 0):
        st.session_state.page_num -= 1
        st.rerun()
with col2:
    st.markdown(
        f"<div style='text-align:center;padding-top:6px;font-weight:600;color:#333'>"
        f"Page {st.session_state.page_num + 1} of {total_pages}</div>",
        unsafe_allow_html=True,
    )
with col3:
    if st.button("Next ▶", use_container_width=True, disabled=st.session_state.page_num == total_pages - 1):
        st.session_state.page_num += 1
        st.rerun()

st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

# Render current page
page_num = st.session_state.page_num
zoom = st.session_state.zoom
page_img = render_page(pdf_bytes, page_num, zoom)
img_w, img_h = page_img.size

st.markdown(
    '<div class="info-box">🖱️ <strong>Click and drag</strong> over text to highlight. '
    'Rectangles are applied when you release the mouse.</div>',
    unsafe_allow_html=True,
)

# Build initial drawings from saved highlights so they persist on re-render
existing_objects = []
page_key = str(page_num)
if page_key in st.session_state.highlights:
    for h in st.session_state.highlights[page_key]:
        rx0, ry0, rx1, ry1 = h["rect"]
        # Convert PDF coords back to canvas coords
        cx0 = rx0 * zoom
        cy0 = ry0 * zoom
        cx1 = rx1 * zoom
        cy1 = ry1 * zoom
        fill = CANVAS_COLORS.get(h["color"], "rgba(255,255,0,0.35)")
        existing_objects.append({
            "type": "rect",
            "left": cx0, "top": cy0,
            "width": cx1 - cx0, "height": cy1 - cy0,
            "fill": fill,
            "stroke": fill,
            "strokeWidth": 0,
            "version": "4.4.0",
        })

canvas_result = st_canvas(
    fill_color=CANVAS_COLORS[color_choice],
    stroke_width=0,
    stroke_color=CANVAS_COLORS[color_choice],
    background_image=page_img,
    update_streamlit=True,
    height=img_h,
    width=img_w,
    drawing_mode="rect",
    initial_drawing={"version": "4.4.0", "objects": existing_objects} if existing_objects else None,
    key=f"canvas_{page_num}",
)

# Process new drawn rectangles
if canvas_result.json_data:
    objects = canvas_result.json_data.get("objects", [])
    if objects:
        new_highlights = []
        for obj in objects:
            if obj.get("type") != "rect":
                continue
            # Canvas coords → PDF coords
            left   = obj.get("left", 0)
            top    = obj.get("top", 0)
            width  = obj.get("width", 0)
            height = obj.get("height", 0)
            scaleX = obj.get("scaleX", 1)
            scaleY = obj.get("scaleY", 1)

            cx0 = left
            cy0 = top
            cx1 = left + width * scaleX
            cy1 = top  + height * scaleY

            # Skip tiny accidental clicks
            if abs(cx1 - cx0) < 5 or abs(cy1 - cy0) < 5:
                continue

            px0, py0 = cx0 / zoom, cy0 / zoom
            px1, py1 = cx1 / zoom, cy1 / zoom

            # Normalise in case user drew right-to-left / bottom-to-top
            px0, px1 = min(px0, px1), max(px0, px1)
            py0, py1 = min(py0, py1), max(py0, py1)

            if snap:
                px0, py0, px1, py1 = snap_to_words(
                    pdf_bytes, page_num, (px0, py0, px1, py1), zoom
                )

            new_highlights.append({
                "rect": [px0, py0, px1, py1],
                "color": color_choice,
            })

        if new_highlights:
            st.session_state.highlights[page_key] = new_highlights

# ── Download section ──────────────────────────────────────────────────────────
st.markdown("---")

total_highlights = sum(len(v) for v in st.session_state.highlights.values())

dl_col, stat_col = st.columns([3, 1])
with stat_col:
    st.markdown(
        f"<div class='stat-box'><strong style='font-size:1.4rem'>{total_highlights}</strong>"
        f"<br><span style='font-size:0.8rem;color:#888'>highlight{'s' if total_highlights != 1 else ''}</span></div>",
        unsafe_allow_html=True,
    )
with dl_col:
    if total_highlights > 0:
        annotated = build_annotated_pdf(pdf_bytes, st.session_state.highlights)
        st.download_button(
            label="⬇️ Download highlighted PDF",
            data=annotated,
            file_name="highlighted.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    else:
        st.info("Draw highlights on the PDF above, then download here.")

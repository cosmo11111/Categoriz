import streamlit as st
import fitz  # PyMuPDF
from streamlit_pdf_viewer import pdf_viewer

st.title("Interactive Privacy Shield 🛡️")

if 'redactions' not in st.session_state:
    st.session_state.redactions = [] # Store coordinates here

uploaded_file = st.file_uploader("Upload Statement", type="pdf")

if uploaded_file:
    # 1. Display the PDF and capture selection events
    # 'annotations' is where we pass back what we've already marked
    v_annotations = st.session_state.redactions
    
    # This component now returns the coordinates of the user's mouse selection
    viewer_output = pdf_viewer(
        input=uploaded_file.read(),
        annotations=v_annotations, # Shows current black boxes
        render_text=True           # Allows text highlighting
    )

    # 2. Capture the "New" selection
    if viewer_output:
        # If the user dragged their mouse, it returns a 'last_selection'
        new_box = viewer_output.get('last_selection')
        if new_box and new_box not in st.session_state.redactions:
            st.session_state.redactions.append(new_box)
            st.rerun() # Refresh to show the new black box

    # 3. Apply the actual Redaction
    if st.button("Permanently Redact & Process"):
        doc = fitz.open(stream=uploaded_file.getvalue(), filetype="pdf")
        
        for box in st.session_state.redactions:
            page = doc[box['page'] - 1] # PDF pages are 0-indexed in fitz
            # Convert viewer coords to PDF coords
            rect = fitz.Rect(box['x'], box['y'], box['x'] + box['w'], box['y'] + box['h'])
            page.add_redact_annot(rect, fill=(0,0,0))
            page.apply_redactions()
        
        final_pdf = doc.write()
        st.success("Sensitive data erased! Sending to AI...")
        # Now pass final_pdf to Gemini

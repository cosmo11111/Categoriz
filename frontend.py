import streamlit as st
import fitz  # PyMuPDF
import io

def redact_pdf(input_pdf_bytes, phrases_to_remove):
    # 1. Open the PDF from memory
    doc = fitz.open(stream=input_pdf_bytes, filetype="pdf")
    
    for page in doc:
        for phrase in phrases_to_remove:
            # 2. Find every instance of the sensitive phrase
            areas = page.search_for(phrase)
            for area in areas:
                # 3. Add a "Redact" annotation
                page.add_redact_annot(area, fill=(0, 0, 0))
        
        # 4. Apply the redactions (this permanently deletes the text)
        page.apply_redactions()
    
    # 5. Save back to a memory buffer
    output_buffer = io.BytesIO()
    doc.save(output_buffer)
    doc.close()
    return output_buffer.getvalue()

# --- UI ---
st.title("Local Redactor")
uploaded_file = st.file_uploader("Upload Statement", type="pdf")

if uploaded_file:
    # User types what they want hidden (Account #, Name, etc.)
    to_hide = st.text_input("Phrases to redact (comma separated)", "Account # 123, John Doe")
    
    if st.button("Redact & Preview"):
        phrases = [p.strip() for p in to_hide.split(",")]
        redacted_data = redact_pdf(uploaded_file.read(), phrases)
        
        st.success("Redaction complete! This version is now safe to send to AI.")
        # Now you would pass 'redacted_data' to your Gemini function

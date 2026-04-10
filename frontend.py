import fitz  # PyMuPDF
import pdfplumber
import tkinter as tk
from PIL import Image, ImageTk

class PDFAnnotator:
    def __init__(self, pdf_path):
        self.doc = fitz.open(pdf_path)
        self.plumber = pdfplumber.open(pdf_path)
        self.page_num = 0
        self.scale = 1.5  # zoom factor
        # ... setup Tkinter window, bind mouse events

    def render_page(self):
        page = self.doc[self.page_num]
        mat = fitz.Matrix(self.scale, self.scale)
        pix = page.get_pixmap(matrix=mat)
        # Convert to PIL Image → ImageTk for display

    def on_drag_end(self, event):
        # Convert screen coords → PDF coords
        x0 = self.drag_start_x / self.scale
        y0 = self.drag_start_y / self.scale
        x1 = event.x / self.scale
        y1 = event.y / self.scale
        # Find words in pdfplumber within that rect
        # Add highlight annotation via fitz
        page = self.doc[self.page_num]
        rect = fitz.Rect(x0, y0, x1, y1)
        page.add_highlight_annot(rect)
        self.doc.save("annotated.pdf")

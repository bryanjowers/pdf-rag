#!/usr/bin/env python3
"""
utils_preprocess.py — Optional PDF preprocessing helpers.
"""

import os
from pathlib import Path
import fitz  # PyMuPDF
import cv2
import numpy as np

def preprocess_pdf(pdf_path: Path) -> Path:
    """
    Extracts pages as images → denoise/deskew → writes to temp PDF.
    Returns new cleaned PDF path.
    """
    temp_pdf = pdf_path.parent / f"{pdf_path.stem}_preprocessed.pdf"

    # Open original PDF
    doc = fitz.open(str(pdf_path))
    new_doc = fitz.open()

    for page_index in range(len(doc)):
        page = doc.load_page(page_index)
        pix = page.get_pixmap(dpi=300)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)

        # --- Simple cleaning ---
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (3, 3), 0)
        cleaned = cv2.fastNlMeansDenoising(blur, h=10)

        # --- Optional threshold (binarize for OCR clarity) ---
        _, thresh = cv2.threshold(cleaned, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Convert back to PDF page
        pix_clean = fitz.Pixmap(fitz.csGRAY, pix.width, pix.height, thresh.tobytes())
        page_img = fitz.open("pdf", pix_clean.tobytes("pdf"))
        new_doc.insert_pdf(page_img)

    new_doc.save(str(temp_pdf))
    new_doc.close()
    print(f"🧹 Saved preprocessed PDF → {temp_pdf}")
    return temp_pdf

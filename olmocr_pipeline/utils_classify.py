#!/usr/bin/env python3
"""
utils_classify.py - PDF classification and validation utilities

Classifies PDFs as scanned vs digital using PyMuPDF text layer detection.
Enforces hard page limits and routing confidence thresholds.
"""

import hashlib
from pathlib import Path
from typing import Dict, Literal, Optional
import fitz  # PyMuPDF


def classify_pdf(
    pdf_path: Path,
    config: Dict
) -> Dict:
    """
    Classify PDF as scanned or digital using PyMuPDF text layer analysis.

    Args:
        pdf_path: Path to PDF file
        config: Configuration dict with classification thresholds

    Returns:
        Dictionary with classification results:
        {
            "type": "pdf_digital" | "pdf_scanned" | "rejected",
            "percent_digital": float,
            "confidence": "high" | "low",
            "total_pages": int,
            "digital_pages": int,
            "allowed": bool,
            "rejection_reason": str | None
        }

    Raises:
        FileNotFoundError: If PDF doesn't exist
        fitz.FitzError: If PDF is corrupted or unreadable
    """
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    # Extract config thresholds
    percent_cutoff = config.get("classification", {}).get("percent_digital_cutoff", 0.75)
    confidence_low_min = config.get("classification", {}).get("confidence_low_min", 0.65)
    confidence_low_max = config.get("classification", {}).get("confidence_low_max", 0.85)
    max_pages = config.get("classification", {}).get("max_pages_absolute", 200)

    # Open PDF and analyze text layers
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        raise fitz.FitzError(f"Failed to open PDF: {e}")

    total_pages = len(doc)
    digital_pages = 0

    # Count pages with extractable text
    for page_num in range(total_pages):
        try:
            page = doc[page_num]
            text = page.get_text().strip()
            if text:
                digital_pages += 1
        except Exception:
            # Skip pages that fail to extract (treat as scanned)
            continue

    doc.close()

    # 🚨 ENFORCE HARD PAGE LIMIT
    if total_pages > max_pages:
        return {
            "type": "rejected",
            "percent_digital": digital_pages / total_pages if total_pages > 0 else 0.0,
            "confidence": "high",
            "total_pages": total_pages,
            "digital_pages": digital_pages,
            "allowed": False,
            "rejection_reason": f"Exceeds {max_pages}-page limit ({total_pages} pages)"
        }

    # Calculate digital percentage
    pct_digital = digital_pages / total_pages if total_pages > 0 else 0.0

    # Determine confidence level
    if pct_digital < confidence_low_min or pct_digital > confidence_low_max:
        confidence = "high"
    else:
        confidence = "low"

    # Route to digital or scanned
    if pct_digital >= percent_cutoff:
        classification_type = "pdf_digital"
    else:
        classification_type = "pdf_scanned"

    return {
        "type": classification_type,
        "percent_digital": pct_digital,
        "confidence": confidence,
        "total_pages": total_pages,
        "digital_pages": digital_pages,
        "allowed": True,
        "rejection_reason": None
    }


def validate_page_limit(
    pdf_path: Path,
    max_pages: int = 200
) -> tuple[bool, Optional[str]]:
    """
    Quick validation: check if PDF exceeds page limit without full classification.

    Args:
        pdf_path: Path to PDF file
        max_pages: Maximum allowed pages

    Returns:
        Tuple of (allowed: bool, rejection_reason: str | None)

    Raises:
        FileNotFoundError: If PDF doesn't exist
        fitz.FitzError: If PDF is corrupted
    """
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    try:
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        doc.close()
    except Exception as e:
        raise fitz.FitzError(f"Failed to open PDF: {e}")

    if total_pages > max_pages:
        return False, f"Exceeds {max_pages}-page limit ({total_pages} pages)"

    return True, None


def compute_file_hash(file_path: Path, algorithm: str = "sha256") -> str:
    """
    Compute hash of input file for deduplication and provenance.

    Args:
        file_path: Path to file
        algorithm: Hash algorithm (default: sha256)

    Returns:
        Hex digest of file hash

    Raises:
        FileNotFoundError: If file doesn't exist
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    hash_obj = hashlib.new(algorithm)

    with file_path.open("rb") as f:
        while chunk := f.read(8192):
            hash_obj.update(chunk)

    return hash_obj.hexdigest()


def validate_file_type(
    file_path: Path,
    allowed_extensions: set[str]
) -> tuple[bool, str]:
    """
    Validate file extension against allowed types.

    Args:
        file_path: Path to file
        allowed_extensions: Set of allowed extensions (e.g., {'.pdf', '.docx'})

    Returns:
        Tuple of (valid: bool, file_type: str)
        file_type will be lowercase extension without dot (e.g., 'pdf', 'docx')
    """
    ext = file_path.suffix.lower()

    if ext in allowed_extensions:
        return True, ext.lstrip('.')

    return False, "unsupported"


def get_mime_type(file_path: Path) -> str:
    """
    Determine MIME type based on file extension.

    Args:
        file_path: Path to file

    Returns:
        MIME type string
    """
    ext = file_path.suffix.lower()

    mime_map = {
        '.pdf': 'application/pdf',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.doc': 'application/msword',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.xls': 'application/vnd.ms-excel',
        '.csv': 'text/csv',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.tif': 'image/tiff',
        '.tiff': 'image/tiff',
        '.msg': 'application/vnd.ms-outlook',
        '.eml': 'message/rfc822'
    }

    return mime_map.get(ext, 'application/octet-stream')


# Supported file types for Phase 2
SUPPORTED_EXTENSIONS = {
    '.pdf',
    '.docx',
    '.xlsx',
    '.csv',
    '.jpg',
    '.jpeg',
    '.png',
    '.tif',
    '.tiff'
}

# File type routing map
FILE_TYPE_HANDLERS = {
    'pdf': 'classify_then_route',  # Requires classification
    'docx': 'docx_handler',
    'xlsx': 'xlsx_handler',
    'csv': 'xlsx_handler',  # CSV uses same handler as XLSX
    'jpg': 'image_handler',
    'jpeg': 'image_handler',
    'png': 'image_handler',
    'tif': 'image_handler',
    'tiff': 'image_handler'
}

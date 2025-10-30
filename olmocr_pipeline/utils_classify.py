#!/usr/bin/env python3
"""
utils_classify.py - PDF classification and validation utilities

Classifies PDFs as scanned vs digital using PyMuPDF text layer detection.
Enforces hard page limits and routing confidence thresholds.
"""

import hashlib
import random
from pathlib import Path
from typing import Dict, Literal, Optional
import fitz  # PyMuPDF


def has_full_page_image(page: fitz.Page) -> bool:
    """
    Check if a single page has a full-page scanned image.

    Uses area coverage (DPI-independent) as primary detection method.
    Pixel dimensions are only used as a backup check.

    Args:
        page: PyMuPDF Page object

    Returns:
        bool: True if page contains a full-page scan (>80% coverage)
    """
    page_rect = page.rect
    page_area = page_rect.width * page_rect.height

    if page_area == 0:
        return False  # Degenerate case

    # ⚡ OPTIMIZATION 3: Lightweight Image Detection
    # Use full=False to avoid extracting image bytes (faster)
    image_list = page.get_images(full=False)

    if not image_list:
        return False  # No images at all

    for img in image_list:
        xref = img[0]

        # PRIMARY METHOD: Area coverage (DPI-independent)
        try:
            # Get the bbox of where the image is placed on the page
            bbox_list = page.get_image_rects(xref)

            if bbox_list:
                # An image can appear multiple times; check all instances
                for bbox in bbox_list:
                    img_area = abs((bbox.x1 - bbox.x0) * (bbox.y1 - bbox.y0))
                    coverage = img_area / page_area

                    if coverage >= 0.80:  # 80%+ coverage = full-page scan
                        return True

        except (RuntimeError, ValueError, AttributeError):
            # If bbox detection fails, use pixel dimension heuristics
            pass  # Fall through to backup method

    # BACKUP METHOD: Pixel dimension heuristics
    # Only used when bbox detection fails (rare)
    for img in image_list:
        xref = img[0]

        try:
            pix = fitz.Pixmap(page.parent, xref)

            # Get page dimensions in points (1 point = 1/72 inch)
            page_width_pts = page_rect.width
            page_height_pts = page_rect.height

            # Convert page points to inches
            page_width_inches = page_width_pts / 72.0
            page_height_inches = page_height_pts / 72.0

            # Calculate image DPI
            img_dpi_x = pix.width / page_width_inches if page_width_inches > 0 else 0
            img_dpi_y = pix.height / page_height_inches if page_height_inches > 0 else 0
            avg_dpi = (img_dpi_x + img_dpi_y) / 2.0

            # Detection heuristics
            is_scan_resolution = avg_dpi >= 50  # Scan quality (50+ DPI)
            min_dimension = min(pix.width, pix.height)
            is_substantial_image = min_dimension >= 500  # At least 500px

            # Check aspect ratio matches page
            img_aspect = pix.height / pix.width if pix.width > 0 else 0
            page_aspect = page_height_pts / page_width_pts if page_width_pts > 0 else 0
            aspect_diff = abs(img_aspect - page_aspect)
            has_matching_aspect = aspect_diff < 0.2  # Within 20%

            # Additional: Check if image is page-sized (for very low DPI scans)
            page_w_px_at_72dpi = page_width_pts
            page_h_px_at_72dpi = page_height_pts
            is_page_sized = (
                (0.8 * page_w_px_at_72dpi <= pix.width <= 5 * page_w_px_at_72dpi) and
                (0.8 * page_h_px_at_72dpi <= pix.height <= 5 * page_h_px_at_72dpi)
            )

            pix = None  # Free memory immediately

            # Detect if: (High quality scan) OR (Page-sized image with matching aspect)
            if (is_scan_resolution and is_substantial_image and has_matching_aspect) or \
               (is_page_sized and has_matching_aspect):
                return True

        except Exception:
            # If pixmap extraction fails, skip this image
            continue

    return False


def detect_full_page_images(pdf_path: Path, config: Dict) -> Dict:
    """
    Check for full-page scanned images using stratified random sampling.

    Strategy:
    - For large PDFs: Random sample with stratification (5 sections)
    - Ensures we check different sections of the document
    - More robust against ordered anomalies (sandwich PDFs)
    - ⚡ Early exit once confident (2-3 scans = clearly scanned)

    Args:
        pdf_path: Path to PDF file
        config: Configuration dict with image_detection settings

    Returns:
        Dict with:
            - has_full_page_scans: bool
            - sampled_pages: int
            - scan_pages: int
            - scan_percentage: float
    """
    try:
        doc = fitz.open(pdf_path)
    except Exception:
        return {
            'has_full_page_scans': False,
            'sampled_pages': 0,
            'scan_pages': 0,
            'scan_percentage': 0.0
        }

    total_pages = len(doc)

    # Get config settings
    img_config = config.get("classification", {}).get("image_detection", {})
    sample_large = img_config.get("sample_large_pdfs", True)
    sample_size = img_config.get("sample_size", 15)
    early_exit_threshold = img_config.get("early_exit_scan_count", 3)  # Stop after 3 scans found

    if sample_large and total_pages > 10:
        # Stratified random sampling for large docs
        # Divide into 5 strata, sample from each
        strata_size = total_pages // 5
        pages_to_check = []

        for i in range(5):
            start = i * strata_size
            end = start + strata_size if i < 4 else total_pages

            # Sample 3 random pages from each stratum
            stratum_sample_size = min(3, end - start)
            if stratum_sample_size > 0:
                stratum_sample = random.sample(range(start, end), stratum_sample_size)
                pages_to_check.extend(stratum_sample)

        # Cap at sample_size
        pages_to_check = sorted(set(pages_to_check))[:sample_size]
    else:
        # Check all pages for small docs (≤10 pages)
        pages_to_check = range(total_pages)

    full_page_scan_count = 0
    checked_pages = 0

    # ⚡ OPTIMIZATION 4: Early Exit Once Confident
    for page_num in pages_to_check:
        try:
            if has_full_page_image(doc[page_num]):
                full_page_scan_count += 1
            checked_pages += 1

            # Early exit if we've found enough scans to be confident
            if full_page_scan_count >= early_exit_threshold:
                doc.close()
                return {
                    'has_full_page_scans': True,
                    'sampled_pages': checked_pages,
                    'scan_pages': full_page_scan_count,
                    'scan_percentage': (full_page_scan_count / checked_pages * 100)
                }

        except Exception:
            # Don't let one bad page break classification
            continue

    doc.close()

    # Conservative threshold: If >50% of sampled pages have scans
    threshold = img_config.get("sample_threshold", 0.50)
    scan_percentage = (full_page_scan_count / checked_pages * 100) if checked_pages > 0 else 0

    return {
        'has_full_page_scans': (full_page_scan_count / checked_pages) >= threshold if checked_pages > 0 else False,
        'sampled_pages': checked_pages,
        'scan_pages': full_page_scan_count,
        'scan_percentage': scan_percentage
    }


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

    # 🚨 ENFORCE HARD PAGE LIMIT
    if total_pages > max_pages:
        doc.close()
        return {
            "type": "rejected",
            "percent_digital": 0.0,
            "confidence": "high",
            "total_pages": total_pages,
            "digital_pages": 0,
            "allowed": False,
            "rejection_reason": f"Exceeds {max_pages}-page limit ({total_pages} pages)"
        }

    # ⚡ OPTIMIZATION 1: Metadata Pre-Scan (Early Exit)
    # Check first 2-3 pages for text before full analysis
    prescan_pages = min(3, total_pages)
    prescan_digital = 0

    for page_num in range(prescan_pages):
        try:
            page = doc[page_num]
            text = page.get_text().strip()
            if text:
                prescan_digital += 1
        except Exception:
            continue

    prescan_pct = prescan_digital / prescan_pages if prescan_pages > 0 else 0.0

    # Early exit if clearly scanned (<5% text in first pages)
    if prescan_pct < 0.05:
        doc.close()
        return {
            "type": "pdf_scanned",
            "percent_digital": prescan_pct,
            "confidence": "high",
            "total_pages": total_pages,
            "digital_pages": prescan_digital,
            "allowed": True,
            "rejection_reason": None,
            "classification_reason": f"Low text yield in pre-scan ({prescan_pct:.1%})"
        }

    # Full text analysis (only if pre-scan indicates some text)
    digital_pages = 0
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

    # Calculate digital percentage
    pct_digital = digital_pages / total_pages if total_pages > 0 else 0.0

    # Determine confidence level
    if pct_digital < confidence_low_min or pct_digital > confidence_low_max:
        confidence = "high"
    else:
        confidence = "low"

    # 🔍 STAGE 2: Image Detection for Pre-OCR'd Scanned PDFs
    # Only check if PDF has substantial text (might be pre-OCR'd scan)
    image_result = None
    classification_reason = None

    if pct_digital >= 0.50:  # Has text, but might be pre-OCR'd
        image_config = config.get("classification", {}).get("image_detection", {})

        if image_config.get("enabled", True):
            image_result = detect_full_page_images(pdf_path, config)

            if image_result['has_full_page_scans']:
                # Override: This is a pre-OCR'd scan, needs real OCR
                classification_type = "pdf_scanned"
                classification_reason = f"Pre-OCR'd scan detected ({image_result['scan_percentage']:.0f}% of sampled pages have full-page images)"
                confidence = "high"  # High confidence in image detection
            else:
                # True digital PDF (has text, no full-page scans)
                classification_type = "pdf_digital"
                classification_reason = f"True digital PDF (no full-page scans detected)"
        else:
            # Image detection disabled, use text-based classification
            classification_type = "pdf_digital" if pct_digital >= percent_cutoff else "pdf_scanned"
    else:
        # Low text yield, clearly a scan
        classification_type = "pdf_scanned"
        classification_reason = f"Low text yield ({pct_digital:.1%})"

    # Build result dict
    result = {
        "type": classification_type,
        "percent_digital": pct_digital,
        "confidence": confidence,
        "total_pages": total_pages,
        "digital_pages": digital_pages,
        "allowed": True,
        "rejection_reason": None,
        "classification_reason": classification_reason
    }

    # Add image detection details if available
    if image_result:
        result["image_detection"] = {
            "has_full_page_scans": image_result['has_full_page_scans'],
            "sampled_pages": image_result['sampled_pages'],
            "scan_pages": image_result['scan_pages'],
            "scan_percentage": image_result['scan_percentage']
        }

    return result


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

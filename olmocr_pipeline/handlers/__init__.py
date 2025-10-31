"""
Document processing handlers for Phase 2 multi-format ingestion.
"""

from .pdf_digital import process_digital_pdf
from .pdf_scanned import process_scanned_pdf, process_scanned_pdf_batch
from .docx import process_docx
from .xlsx import process_xlsx
from .image import process_image

__all__ = [
    'process_digital_pdf',
    'process_scanned_pdf',
    'process_scanned_pdf_batch',
    'process_docx',
    'process_xlsx',
    'process_image'
]

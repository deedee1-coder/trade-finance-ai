from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import pdfplumber
    _HAS_PDFPLUMBER = True
except ImportError:
    _HAS_PDFPLUMBER = False


def extract_text(pdf_path: Path) -> str:
    if not _HAS_PDFPLUMBER:
        return f"[pdfplumber not installed — cannot read {pdf_path.name}]"
    text_parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text_parts.append(t)
    return "\n".join(text_parts).strip()


def extract_pages(pdf_path: Path) -> list[dict]:
    if not _HAS_PDFPLUMBER:
        return [{"page": 1, "text": "[pdfplumber not installed]"}]
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            pages.append({"page": i, "text": page.extract_text() or ""})
    return pages


def text_quality_score(pages: list[dict]) -> float:
    """
    Return a quality score (0.0–1.0) based on average characters per page.

    Used by both Agent B's confidence multiplier and extract_pages_smart()
    to decide whether OCR is needed.  Thresholds:
      >= 400 chars/page → 1.00  (clean born-digital PDF)
      >= 150            → 0.85
      >= 50             → 0.65
      <  50             → 0.50  (almost certainly a scanned image)
    """
    if not pages:
        return 0.0
    chars_per_page = sum(len(p["text"]) for p in pages) / len(pages)
    if chars_per_page >= 400:
        return 1.0
    if chars_per_page >= 150:
        return 0.85
    if chars_per_page >= 50:
        return 0.65
    return 0.5


def extract_pages_smart(
    pdf_path: Path,
    ocr_threshold: float = 0.65,
    ocr_dpi: int = 200,
) -> tuple[list[dict], bool]:
    """
    Extract text from *pdf_path*, automatically falling back to OCR when native
    text quality is below *ocr_threshold*.

    Returns:
        (pages, ocr_used)  where *pages* has the same format as extract_pages()
        and *ocr_used* is True when the OCR fallback was triggered.

    The function never raises: if OCR is unavailable or fails, it returns the
    native-extraction result with ocr_used=False and logs a warning.
    """
    from core.ocr_utils import extract_text_ocr, ocr_available  # lazy — avoids hard dep

    pages = extract_pages(pdf_path)
    quality = text_quality_score(pages)

    if quality >= ocr_threshold:
        return pages, False

    # Below threshold — try OCR
    if not ocr_available():
        logger.warning(
            "%s: text quality %.2f is below threshold %.2f — OCR would help, "
            "but PyMuPDF/Tesseract is not installed. "
            "Install with: pip install PyMuPDF pytesseract",
            pdf_path.name, quality, ocr_threshold,
        )
        return pages, False

    logger.info(
        "%s: text quality %.2f < %.2f — switching to OCR (dpi=%d)",
        pdf_path.name, quality, ocr_threshold, ocr_dpi,
    )
    try:
        ocr_pages = extract_text_ocr(pdf_path, dpi=ocr_dpi)
        return ocr_pages, True
    except Exception as exc:
        logger.warning(
            "OCR failed for %s: %s — falling back to native text extraction",
            pdf_path.name, exc,
        )
        return pages, False


def classify_by_filename(filename: str) -> str:
    name = filename.lower().replace("-", "_")
    if "letter_of_credit" in name or name.startswith("lc"):
        return "letter_of_credit"
    if "bill_of_lading" in name or "bol" in name:
        return "bill_of_lading"
    if "commercial_invoice" in name or "invoice" in name:
        return "commercial_invoice"
    if "packing_list" in name or "packing" in name:
        return "packing_list"
    if "certificate_of_origin" in name or "origin" in name:
        return "certificate_of_origin"
    if "inspection" in name:
        return "inspection_certificate"
    if "insurance" in name:
        return "insurance_certificate"
    if "sanctions" in name or "policy" in name:
        return "sanctions_policy"
    return "unknown"

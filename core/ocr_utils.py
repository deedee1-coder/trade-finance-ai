"""
OCR utilities for degraded / scanned PDF documents.

Requires two optional dependencies:
  - PyMuPDF  (pip install PyMuPDF)   — renders PDF pages to images
  - pytesseract (pip install pytesseract) + the Tesseract binary
    https://github.com/tesseract-ocr/tesseract

When either dependency is missing the functions raise RuntimeError.
Callers should check ocr_available() before calling extract_text_ocr().
"""
from __future__ import annotations

import io
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Optional-dependency guards ────────────────────────────────────────────────

try:
    import fitz  # PyMuPDF
    _HAS_FITZ = True
except ImportError:
    _HAS_FITZ = False

try:
    import pytesseract
    from PIL import Image as _PILImage  # already in requirements.txt
    _HAS_PYTESSERACT = True
except ImportError:
    _HAS_PYTESSERACT = False


def ocr_available() -> bool:
    """
    Return True only when PyMuPDF, pytesseract, and the Tesseract binary
    are all present and functional.
    """
    if not _HAS_FITZ or not _HAS_PYTESSERACT:
        return False
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def _pdf_to_pil_images(pdf_path: Path, dpi: int) -> list[tuple[int, "_PILImage.Image"]]:
    """Render each page of *pdf_path* to a PIL Image at *dpi* resolution."""
    from PIL import Image

    doc = fitz.open(str(pdf_path))
    zoom = dpi / 72.0  # PyMuPDF native resolution is 72 DPI
    matrix = fitz.Matrix(zoom, zoom)
    pages: list[tuple[int, Image.Image]] = []

    for i in range(len(doc)):
        pixmap = doc[i].get_pixmap(matrix=matrix)
        img = Image.open(io.BytesIO(pixmap.tobytes("png")))
        pages.append((i + 1, img))

    doc.close()
    return pages


def extract_text_ocr(pdf_path: Path, dpi: int = 200) -> list[dict]:
    """
    Extract text from *pdf_path* using OCR (for degraded / scanned documents).

    Returns a list of {"page": int, "text": str} dicts — identical format to
    pdf_utils.extract_pages(), so callers need no special handling.

    Raises RuntimeError if PyMuPDF or Tesseract are not installed.
    """
    if not _HAS_FITZ:
        raise RuntimeError(
            "PyMuPDF is required for OCR-based PDF rendering. "
            "Install it with:  pip install PyMuPDF"
        )
    if not _HAS_PYTESSERACT:
        raise RuntimeError(
            "pytesseract is required for OCR text recognition. "
            "Install it with:  pip install pytesseract  "
            "then install the Tesseract binary: "
            "https://github.com/tesseract-ocr/tesseract"
        )

    pil_pages = _pdf_to_pil_images(pdf_path, dpi=dpi)
    results: list[dict] = []

    for page_num, image in pil_pages:
        text: str = pytesseract.image_to_string(image, lang="eng")
        cleaned = text.strip()
        results.append({"page": page_num, "text": cleaned})
        logger.debug("OCR page %d: %d chars", page_num, len(cleaned))

    total_chars = sum(len(r["text"]) for r in results)
    logger.info(
        "OCR complete — %s: %d page(s), %d total chars",
        pdf_path.name, len(results), total_chars,
    )
    return results

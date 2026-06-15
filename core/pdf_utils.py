from pathlib import Path

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

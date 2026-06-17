"""
Agent B - Field Extraction

Responsibilities:
- Convert each document's raw text into structured, machine-readable fields
- Assign a confidence score (0–1) to every extracted value
- Flag low-confidence fields (e.g. degraded scans, handwritten additions) for
  manual review routing
- Output bounding-box / page-position references for traceability
- Aggregate data across all presented documents for consistent cross-doc matching

Inputs:  runs/{run_id}/context.json  +  input_path/ PDFs
Outputs: runs/{run_id}/extracted_docs.json

Standalone mode: if context.json is absent, Agent B scans the input_path folder
directly and classifies documents by filename — satisfying the "Agent Independence"
requirement from the project spec.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from core.config import settings
from core.llm_client import call_claude, parse_json_response
from core.pdf_utils import classify_by_filename, extract_pages
from core.schemas import ExtractedDocument, ExtractedDocs, ExtractedField

logger = logging.getLogger(__name__)

# Fields with confidence below this are added to low_confidence_fields
CONFIDENCE_THRESHOLD = 0.70

# Per-doc-type fields Agent B will ask Claude to extract.
# Each entry is (field_name, description) so the prompt is self-documenting.
FIELD_DEFINITIONS: dict[str, list[tuple[str, str]]] = {
    "letter_of_credit": [
        ("lc_number",                 "Documentary credit number"),
        ("issuing_bank",              "Name of the issuing bank"),
        ("advising_bank",             "Name of the advising bank, if any"),
        ("applicant_name",            "Applicant / buyer name"),
        ("applicant_country",         "Applicant country"),
        ("beneficiary_name",          "Beneficiary / seller name"),
        ("beneficiary_country",       "Beneficiary country"),
        ("amount",                    "Credit amount as a number (no currency symbol)"),
        ("currency",                  "Currency code, e.g. USD"),
        ("expiry_date",               "Expiry date in YYYY-MM-DD format"),
        ("latest_shipment_date",      "Latest date of shipment in YYYY-MM-DD format"),
        ("port_of_loading",           "Port or place of loading / taking in charge"),
        ("port_of_discharge",         "Port or place of discharge / final destination"),
        ("goods_description",         "Brief description of the goods"),
        ("partial_shipments_allowed", "true if partial shipments are allowed, false if prohibited"),
        ("transhipment_allowed",      "true if transhipment is allowed, false if prohibited"),
        ("presentation_period_days",  "Number of days after shipment to present documents"),
    ],
    "commercial_invoice": [
        ("invoice_number",   "Invoice reference number"),
        ("invoice_date",     "Invoice date in YYYY-MM-DD format"),
        ("seller_name",      "Seller / exporter name"),
        ("seller_country",   "Seller country"),
        ("buyer_name",       "Buyer / importer name"),
        ("buyer_country",    "Buyer country"),
        ("goods_description","Description of goods"),
        ("quantity",         "Total quantity with unit"),
        ("unit_price",       "Unit price as a number"),
        ("total_amount",     "Total invoice amount as a number"),
        ("currency",         "Currency code, e.g. USD"),
        ("payment_terms",    "Payment terms, e.g. 30 days net"),
        ("incoterms",        "Incoterms rule, e.g. CIF"),
    ],
    "bill_of_lading": [
        ("bl_number",         "Bill of lading reference number"),
        ("bl_date",           "Date of issue in YYYY-MM-DD format"),
        ("shipper_name",      "Shipper / consignor name"),
        ("consignee_name",    "Consignee name"),
        ("notify_party",      "Notify party name"),
        ("vessel_name",       "Name of the vessel or carrier"),
        ("voyage_number",     "Voyage or flight number"),
        ("port_of_loading",   "Port of loading"),
        ("port_of_discharge", "Port of discharge"),
        ("goods_description", "Description of goods"),
        ("quantity",          "Total quantity with unit"),
        ("gross_weight",      "Gross weight with unit"),
        ("freight_terms",     "Freight terms, e.g. PREPAID or COLLECT"),
    ],
    "packing_list": [
        ("pl_date",            "Packing list date in YYYY-MM-DD format"),
        ("shipper_name",       "Shipper name"),
        ("consignee_name",     "Consignee name"),
        ("goods_description",  "Description of goods packed"),
        ("total_packages",     "Total number of packages/cartons"),
        ("total_gross_weight", "Total gross weight with unit"),
        ("total_net_weight",   "Total net weight with unit"),
        ("marks_and_numbers",  "Shipping marks and numbers"),
    ],
    "certificate_of_origin": [
        ("co_number",           "Certificate of origin reference number"),
        ("co_date",             "Issue date in YYYY-MM-DD format"),
        ("exporter_name",       "Exporter / producer name"),
        ("exporter_country",    "Exporter country"),
        ("consignee_name",      "Consignee name"),
        ("goods_description",   "Description of goods"),
        ("country_of_origin",   "Country where goods were produced"),
        ("certifying_authority","Authority or chamber that certified the document"),
    ],
    "inspection_certificate": [
        ("ic_number",          "Inspection certificate number"),
        ("ic_date",            "Inspection date in YYYY-MM-DD format"),
        ("inspection_body",    "Name of the inspection company or body"),
        ("goods_description",  "Description of inspected goods"),
        ("quantity_inspected", "Quantity inspected with unit"),
        ("inspection_result",  "Pass / Fail / Conditional result"),
        ("remarks",            "Any remarks or conditions noted"),
    ],
    "insurance_certificate": [
        ("policy_number",    "Insurance policy or certificate number"),
        ("issue_date",       "Date of issue in YYYY-MM-DD format"),
        ("insured_party",    "Name of the insured party"),
        ("goods_description","Description of insured goods"),
        ("insured_amount",   "Insured amount as a number"),
        ("currency",         "Currency code"),
        ("coverage_type",    "Type of coverage, e.g. All Risks"),
        ("voyage",           "Voyage or transit route covered"),
    ],
}

_GENERIC_FIELDS: list[tuple[str, str]] = [
    ("document_date",    "Date of the document in YYYY-MM-DD format"),
    ("issuer_name",      "Name of the issuing party or organisation"),
    ("reference_number", "Any reference or document number"),
    ("goods_description","Description of goods if present"),
    ("parties_mentioned","Comma-separated list of named parties"),
]


def _build_extraction_prompt(doc_type: str, pages: list[dict]) -> tuple[str, str]:
    """Return (system_prompt, user_message) for Claude."""
    field_defs = FIELD_DEFINITIONS.get(doc_type, _GENERIC_FIELDS)
    fields_block = "\n".join(
        f'  "{name}": {{"value": ..., "confidence": 0.0–1.0, "page": <page_number>}}  // {desc}'
        for name, desc in field_defs
    )

    page_text = "\n\n".join(
        f"--- PAGE {p['page']} ---\n{p['text']}" for p in pages if p["text"].strip()
    )
    if not page_text:
        page_text = "[NO READABLE TEXT — document may be a scanned image]"

    system = (
        "You are a trade finance document extraction specialist. "
        "Extract structured fields from the provided document text with high precision. "
        "Assign a confidence score (0.0–1.0) to each field:\n"
        "  1.0 = value is explicitly and unambiguously stated\n"
        "  0.8 = value is clearly present but requires minor inference\n"
        "  0.6 = value is partially readable or inferred from context\n"
        "  0.3 = value is a best guess from very limited text\n"
        "  0.0 = value not found — set value to null\n"
        "Always output ONLY valid JSON. No prose, no markdown fences."
    )

    user = (
        f"Document type: {doc_type.replace('_', ' ').upper()}\n\n"
        f"Extract the following fields and return a single JSON object:\n"
        f"{{\n{fields_block}\n}}\n\n"
        f"Document text (by page):\n{page_text}"
    )

    return system, user


def _assess_text_quality(pages: list[dict]) -> float:
    """
    Return a base confidence multiplier (0.5–1.0) based on text density.
    Sparse text signals a degraded scan; downstream per-field confidences
    are scaled accordingly so low-quality docs naturally surface more flags.
    """
    total_chars = sum(len(p["text"]) for p in pages)
    page_count = max(len(pages), 1)
    chars_per_page = total_chars / page_count

    if chars_per_page >= 400:
        return 1.0
    if chars_per_page >= 150:
        return 0.85
    if chars_per_page >= 50:
        return 0.65
    return 0.5  # very sparse — likely scanned


def _extract_document(pdf_path: Path, doc_type: str) -> ExtractedDocument:
    """Extract structured fields from a single PDF and return an ExtractedDocument."""
    pages = extract_pages(pdf_path)
    text_quality = _assess_text_quality(pages)

    system_prompt, user_message = _build_extraction_prompt(doc_type, pages)

    try:
        raw_response = call_claude(system_prompt, user_message)
        raw_fields: dict = parse_json_response(raw_response)
    except Exception as exc:
        logger.warning("Claude extraction failed for %s: %s", pdf_path.name, exc)
        raw_fields = {}

    # Build ExtractedField objects, applying the text-quality multiplier
    fields: dict[str, ExtractedField] = {}
    for field_name, raw_val in raw_fields.items():
        if not isinstance(raw_val, dict):
            continue
        raw_conf = float(raw_val.get("confidence", 0.0))
        adjusted_conf = round(min(raw_conf * text_quality, 1.0), 3)
        fields[field_name] = ExtractedField(
            value=raw_val.get("value"),
            confidence=adjusted_conf,
            page=int(raw_val.get("page", 1)),
        )

    low_confidence = [
        name for name, f in fields.items()
        if f.confidence < CONFIDENCE_THRESHOLD
    ]

    overall = (
        round(sum(f.confidence for f in fields.values()) / len(fields), 3)
        if fields else 0.0
    )

    # Keep a short raw text snippet for audit trail (first 500 chars of page 1)
    snippet = next((p["text"][:500] for p in pages if p["text"].strip()), "")

    if text_quality < 0.7:
        logger.warning(
            "%s: sparse text detected (quality=%.2f) — OCR fallback recommended",
            pdf_path.name, text_quality,
        )

    return ExtractedDocument(
        doc_type=doc_type,
        filename=pdf_path.name,
        fields=fields,
        overall_confidence=overall,
        low_confidence_fields=low_confidence,
        raw_text_snippet=snippet,
    )


def _load_context(run_dir: Path) -> dict | None:
    context_path = run_dir / "context.json"
    if context_path.exists():
        return json.loads(context_path.read_text(encoding="utf-8"))
    return None


def run(run_id: str, input_path: Path) -> ExtractedDocs:
    """
    Main entry point for Agent B.

    Args:
        run_id:     Unique identifier for this pipeline run.
        input_path: Folder containing the trade bundle PDFs.

    Returns:
        ExtractedDocs — also written to runs/{run_id}/extracted_docs.json.
    """
    run_dir = settings.RUN_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    context = _load_context(run_dir)

    # Build a mapping of filename → doc_type from context (if available)
    # or fall back to filename-based classification.
    if context and context.get("presented_documents"):
        doc_map: dict[str, str] = {
            d["filename"]: d["doc_type"]
            for d in context["presented_documents"]
        }
        logger.info("Agent B: loaded document map from context.json (%d docs)", len(doc_map))
    else:
        logger.info("Agent B: no context.json found — classifying docs by filename (standalone mode)")
        doc_map = {
            p.name: classify_by_filename(p.name)
            for p in sorted(input_path.glob("*.pdf"))
        }

    if not doc_map:
        logger.warning("Agent B: no PDF documents found in %s", input_path)

    extracted_docs = ExtractedDocs(run_id=run_id)

    for filename, doc_type in doc_map.items():
        pdf_path = input_path / filename
        if not pdf_path.exists():
            logger.warning("Agent B: expected file not found — %s", pdf_path)
            continue

        logger.info("Agent B: extracting %s (type=%s)", filename, doc_type)
        doc = _extract_document(pdf_path, doc_type)
        extracted_docs.documents.append(doc)

        if doc.low_confidence_fields:
            logger.warning(
                "Agent B: %s has %d low-confidence field(s): %s",
                filename,
                len(doc.low_confidence_fields),
                ", ".join(doc.low_confidence_fields),
            )

    # Write output artifact
    out_path = run_dir / "extracted_docs.json"
    out_path.write_text(
        extracted_docs.model_dump_json(indent=2),
        encoding="utf-8",
    )
    logger.info("Agent B: wrote %s", out_path)

    return extracted_docs


# ── Standalone execution ──────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    if len(sys.argv) < 3:
        print("Usage: python -m agents.agent_b_extraction <run_id> <input_path>")
        sys.exit(1)

    _run_id = sys.argv[1]
    _input_path = Path(sys.argv[2])

    result = run(_run_id, _input_path)
    print(f"\nExtracted {len(result.documents)} document(s):")
    for doc in result.documents:
        print(
            f"  {doc.filename} ({doc.doc_type}) — "
            f"overall_confidence={doc.overall_confidence:.2f}, "
            f"low_confidence_fields={doc.low_confidence_fields or 'none'}"
        )

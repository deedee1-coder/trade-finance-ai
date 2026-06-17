"""Agent A: Document Intake and Context."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import yaml

from core.config import settings
from core.pdf_utils import extract_pages, classify_by_filename


DEFAULT_REQUIRED_DOCUMENTS = [
    "letter_of_credit.pdf",
    "commercial_invoice.pdf",
    "bill_of_lading.pdf",
    "packing_list.pdf",
    "certificate_of_origin.pdf",
]

# Labels we look for in the Letter of Credit, mapped to the short name we store them under.
# The L/C is written as "Label: value" lines, so we just match the label and keep the value.
LC_TERM_LABELS = {
    "l/c number": "lc_number",
    "lc number": "lc_number",
    "credit number": "lc_number",
    "currency": "currency",
    "amount": "amount",
    "expiry date": "expiry_date",
    "date and place of expiry": "expiry_date",
    "latest shipment date": "latest_shipment_date",
    "applicant": "applicant",
    "beneficiary": "beneficiary",
    "issuing bank": "issuing_bank",
    "advising bank": "advising_bank",
    "port of loading": "port_of_loading",
    "port of discharge": "port_of_discharge",
    "goods description": "goods_description",
    "partial shipments": "partial_shipments",
    "transhipment": "transhipment",
    "icc rules": "icc_rules",
    "presentation period": "presentation_period",
}

# Places we treat as higher risk. Kept short and obvious on purpose.
HIGH_RISK_PLACES = ["iran", "north korea", "syria", "russia", "crimea", "restrictedland", "riskland"]


def run(bundle_path: str | Path) -> Path:
    # Reads the bundle, validates files, creates a run folder, and writes the context packet.
    bundle_path = Path(bundle_path).resolve()
    if not bundle_path.exists() or not bundle_path.is_dir():
        raise FileNotFoundError(f"Bundle folder not found: {bundle_path}")

    manifest_path = bundle_path / "manifest.yaml"
    if not manifest_path.exists():
        raise FileNotFoundError(f"manifest.yaml not found in bundle: {bundle_path}")

    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    required_documents = manifest.get("required_documents") or DEFAULT_REQUIRED_DOCUMENTS
    manifest_documents = manifest.get("documents") or {}

    run_id = _next_run_id()
    run_dir = settings.RUN_DIR / run_id
    input_dir = run_dir / "input_documents"
    input_dir.mkdir(parents=True, exist_ok=False)

    documents = []
    missing_documents = []

    for filename in required_documents:
        source_path = bundle_path / filename
        present = source_path.exists()
        if not present:
            missing_documents.append(filename)

        copied_path = None
        if present:
            copied_path = input_dir / filename
            shutil.copy2(source_path, copied_path)

        document_type = _document_type_for(filename, manifest_documents)
        documents.append(
            {
                "document_type": document_type,
                "doc_type": document_type,
                "filename": filename,
                "source_path": str(source_path),
                "run_path": str(copied_path) if copied_path else None,
                "required": True,
                "present": present,
            }
        )

    extra_files = []
    for path in sorted(bundle_path.iterdir()):
        if path.name == "manifest.yaml" or path.name in required_documents:
            continue
        if path.is_file():
            extra_files.append(path.name)

    case_metadata_path = bundle_path / "case_metadata.json"
    if case_metadata_path.exists():
        shutil.copy2(case_metadata_path, run_dir / "case_metadata.json")

    # Read the Letter of Credit to capture the key deal terms and remember where each came from.
    lc_terms: dict = {}
    evidence_index: dict = {}
    lc_text = ""
    lc_document = next(
        (doc for doc in documents if doc["doc_type"] == "letter_of_credit" and doc["present"]),
        None,
    )
    if lc_document is not None:
        lc_pages = extract_pages(Path(lc_document["run_path"]))
        lc_text = "\n".join(page["text"] for page in lc_pages)
        lc_terms, evidence_index = _read_lc_terms(lc_pages, lc_document["filename"])

    risk_flags = _detect_risks(lc_text, missing_documents, extra_files)

    context_packet = {
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "input_path": str(bundle_path),
        "bundle_path": str(bundle_path),
        "manifest_path": str(manifest_path),
        "manifest": manifest,
        "required_documents": required_documents,
        "documents": documents,
        "presented_documents": [doc for doc in documents if doc["present"]],
        "missing_documents": missing_documents,
        "extra_files": extra_files,
        "lc_terms": lc_terms,
        "evidence_index": evidence_index,
        "risk_flags": risk_flags,
        "status": "ready" if not missing_documents else "missing_documents",
    }

    _write_json(run_dir / "context_packet.json", context_packet)
    _write_json(run_dir / "context.json", context_packet)
    _write_text(run_dir / "audit_log.md", _audit_log(context_packet))
    return run_dir


def _next_run_id() -> str:
    # Creates run_001, run_002, and so on.
    settings.RUN_DIR.mkdir(parents=True, exist_ok=True)
    numbers = []
    for path in settings.RUN_DIR.glob("run_*"):
        suffix = path.name.replace("run_", "")
        if path.is_dir() and suffix.isdigit():
            numbers.append(int(suffix))
    return f"run_{max(numbers, default=0) + 1:03d}"


def _document_type_for(filename: str, manifest_documents: dict) -> str:
    # First trust the manifest's type for this filename; otherwise guess from the filename.
    for document_type, manifest_filename in manifest_documents.items():
        if manifest_filename == filename:
            return document_type
    return classify_by_filename(filename)


def _read_lc_terms(lc_pages: list[dict], lc_filename: str) -> tuple[dict, dict]:
    # Reads the Letter of Credit line by line and copies the key terms into a dictionary.
    # For every term, also records which document and page it came from (the evidence index).
    terms: dict = {}
    evidence: dict = {}
    for page in lc_pages:
        page_number = page["page"]
        for line in page["text"].splitlines():
            if ":" not in line:
                continue
            label_part, value_part = line.split(":", 1)
            label = label_part.strip().lower()
            value = value_part.strip()
            key = LC_TERM_LABELS.get(label)
            if key and value and key not in terms:
                terms[key] = value
                evidence[key] = {"document": lc_filename, "page": page_number}
    return terms, evidence


def _detect_risks(lc_text: str, missing_documents: list, extra_files: list) -> list:
    # A few simple, easy-to-explain checks that flag anything worth a closer look.
    flags = []
    for filename in missing_documents:
        flags.append(f"Missing required document: {filename}")

    lowered = lc_text.lower()
    for place in HIGH_RISK_PLACES:
        if place in lowered:
            flags.append(f"High-risk jurisdiction mentioned in Letter of Credit: {place.title()}")

    # Only an unexpected PDF counts as an "unusual document"; JSON sidecars are ignored.
    for filename in extra_files:
        if filename.lower().endswith(".pdf"):
            flags.append(f"Unexpected extra document in bundle: {filename}")

    return flags


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _audit_log(context_packet: dict) -> str:
    lines = [
        "# Agent A Audit Log",
        "",
        f"Run ID: {context_packet['run_id']}",
        f"Bundle: {context_packet['bundle_path']}",
        f"Status: {context_packet['status']}",
        "",
        "## Documents",
    ]
    for document in context_packet["documents"]:
        marker = "present" if document["present"] else "missing"
        lines.append(f"- {document['filename']}: {marker}")

    lines.extend([
        "",
        "## Context",
        f"- L/C terms captured: {len(context_packet['lc_terms'])}",
        f"- Evidence index entries: {len(context_packet['evidence_index'])}",
        f"- Risk flags: {len(context_packet['risk_flags'])}",
    ])
    for flag in context_packet["risk_flags"]:
        lines.append(f"  - {flag}")
    return "\n".join(lines) + "\n"

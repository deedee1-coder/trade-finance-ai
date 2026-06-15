"""Agent A: Document Intake and Context."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import yaml

from core.config import settings


DEFAULT_REQUIRED_DOCUMENTS = [
    "letter_of_credit.pdf",
    "commercial_invoice.pdf",
    "bill_of_lading.pdf",
    "packing_list.pdf",
    "certificate_of_origin.pdf",
]


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
        "evidence_index": {},
        "risk_flags": [],
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
    # Finds the logical document type from the manifest.
    for document_type, manifest_filename in manifest_documents.items():
        if manifest_filename == filename:
            return document_type
    return Path(filename).stem


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
    return "\n".join(lines) + "\n"
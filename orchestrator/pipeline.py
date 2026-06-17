"""Main pipeline runner for the deterministic agent workflow."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from agents.agent_a_intake import run as run_agent_a
from agents.agent_h_triage import run as run_agent_h


def run_pipeline(input_path: str | Path) -> Path:
    # Agent A creates the run folder and context files.
    run_dir = run_agent_a(input_path)
    run_id = run_dir.name
    input_documents_dir = run_dir / "input_documents"

    step_results: list[dict[str, Any]] = []

    _run_step(step_results, "agent_b_extraction", lambda: _run_agent_b(run_id, input_documents_dir))
    _write_extracted_fields_compat(run_dir)
    _run_step(step_results, "agent_c_ucp600", lambda: _run_agent_c(run_dir))
    _run_step(step_results, "agent_d_matching", lambda: _run_agent_d(run_dir))
    _run_step(step_results, "agent_e_sanctions", lambda: _run_agent_e(run_dir))

    # Agent H is intentionally last and defensive. It can still decide MANUAL_REVIEW
    # when an upstream artifact is missing or an earlier agent failed.
    _run_step(step_results, "agent_h_triage", lambda: run_agent_h(run_dir))

    _write_json(
        run_dir / "pipeline_status.json",
        {
            "run_id": run_id,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "steps": step_results,
        },
    )
    return run_dir


def _run_step(step_results: list[dict[str, Any]], name: str, callback: Callable[[], Any]) -> None:
    try:
        callback()
        step_results.append({"agent": name, "status": "completed"})
    except Exception as exc:
        step_results.append({"agent": name, "status": "failed", "error": str(exc)})


def _run_agent_b(run_id: str, input_documents_dir: Path) -> None:
    from agents.agent_b_extraction import run as run_agent_b

    run_agent_b(run_id, input_documents_dir)


def _run_agent_c(run_dir: Path) -> None:
    from agents.agent_c_ucp600 import run as run_agent_c

    run_agent_c(run_dir)


def _run_agent_d(run_dir: Path) -> None:
    from agents.agent_d_matching import run as run_agent_d

    run_agent_d(run_dir)


def _run_agent_e(run_dir: Path) -> None:
    from agents.agent_e_sanctions import run as run_agent_e

    run_agent_e(run_dir)


def _write_extracted_fields_compat(run_dir: Path) -> None:
    # Temporary compatibility layer: B writes extracted_docs.json, while C/D/E currently
    # consume extracted_fields.json. This should be removed once all agents share one schema.
    extracted_docs_path = run_dir / "extracted_docs.json"
    if not extracted_docs_path.exists():
        return

    extracted_docs = _read_json(extracted_docs_path)
    context = _read_json(run_dir / "context.json") or _read_json(run_dir / "context_packet.json")
    case_id = (context.get("manifest") or {}).get("case_id") or context.get("case_id") or run_dir.name

    compatibility: dict[str, Any] = {"case_id": case_id}
    for document in extracted_docs.get("documents", []):
        doc_type = document.get("doc_type") or document.get("document_type") or "unknown"
        fields = document.get("fields", {})
        compatibility[doc_type] = _flatten_fields(fields)

    _apply_field_aliases(compatibility)
    _write_json(run_dir / "extracted_fields.json", compatibility)


def _flatten_fields(fields: dict[str, Any]) -> dict[str, Any]:
    flattened = {}
    for field_name, field_payload in fields.items():
        if isinstance(field_payload, dict) and "value" in field_payload:
            flattened[field_name] = field_payload.get("value")
        else:
            flattened[field_name] = field_payload
    return flattened


def _apply_field_aliases(extracted: dict[str, Any]) -> None:
    lc = extracted.get("letter_of_credit", {})
    invoice = extracted.get("commercial_invoice", {})
    bol = extracted.get("bill_of_lading", {})
    coo = extracted.get("certificate_of_origin", {})

    _copy_alias(lc, "applicant_name", "applicant")
    _copy_alias(lc, "beneficiary_name", "beneficiary")
    _copy_alias(lc, "presentation_period_days", "presentation_rule_days")

    _copy_alias(invoice, "total_amount", "amount")
    _copy_alias(invoice, "buyer_name", "buyer")
    _copy_alias(invoice, "seller_name", "seller")

    _copy_alias(bol, "consignee_name", "consignee")
    _copy_alias(bol, "shipper_name", "shipper")
    _copy_alias(bol, "bl_date", "shipment_date")

    _copy_alias(coo, "exporter_name", "exporter")


def _copy_alias(payload: dict[str, Any], source: str, target: str) -> None:
    if source in payload and target not in payload:
        payload[target] = payload[source]


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
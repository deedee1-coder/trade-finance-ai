"""Agent G: Discrepancy waiver classification."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from core.config import settings


WAIVABLE_AUTO = "WAIVABLE_AUTO"
WAIVABLE_NEEDS_APPLICANT = "WAIVABLE_NEEDS_APPLICANT"
NON_WAIVABLE = "NON_WAIVABLE"

# Fraud check IDs that represent authenticity failures — never waivable.
_NON_WAIVABLE_FRAUD_CHECKS = frozenset({"FRD-001", "FRD-002", "FRD-003"})

# Minor data-quality / input-validation checks that never block a decision.
_DATA_QUALITY_CHECKS = frozenset({"UCP-004", "INPUT-001", "INPUT-002", "INPUT-003"})

# Source files to load, in priority order per source name.
_SOURCE_FILES = [
    ("ucp",      ["ucp_result.json"]),
    ("matching", ["match_result.json"]),
    ("sanctions",["sanctions_screen.json", "sanctions_result.json"]),
    ("fraud",    ["fraud_screen.json"]),
]

_NEEDS_APPLICANT_RATIONALES: dict[str, str] = {
    "MATCH-001": "Amount discrepancy exceeds pre-authorized tolerance — applicant must confirm acceptance.",
    "MATCH-003": "Applicant/buyer/consignee name mismatch — applicant must confirm all parties are the same entity.",
    "MATCH-004": "Beneficiary/seller/shipper name mismatch — applicant must confirm all parties are the same entity.",
    "UCP-002":   "Late shipment — applicant must authorize acceptance of late-shipped goods.",
    "UCP-003":   "Late presentation — applicant may waive the deadline per UCP 600 Art. 29.",
    "UCP-005":   "Partial shipment against prohibition — applicant must authorize acceptance.",
    "UCP-006":   "Transhipment against prohibition — applicant must authorize acceptance.",
    "FRD-001":   "Authenticity concern on a supporting document — applicant should confirm.",
}


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


def _read_policy(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return {}


def _classify(finding: dict[str, Any], policy: dict[str, Any]) -> tuple[str, str]:
    """Return (waiver_status, rationale) for a single finding."""
    severity = str(finding.get("severity", "minor")).lower()
    check_id = str(finding.get("check_id", ""))
    source = str(finding.get("source", finding.get("agent_name", ""))).lower()
    status = str(finding.get("status", ""))
    explanation = str(finding.get("explanation", "")).lower()

    # --- NON_WAIVABLE ---

    if severity == "critical":
        return NON_WAIVABLE, "Critical findings require immediate escalation and cannot be waived."

    if "sanction" in source or "agent e" in source:
        return NON_WAIVABLE, "Sanctions findings cannot be waived."

    if check_id in _NON_WAIVABLE_FRAUD_CHECKS and status == "failed":
        return NON_WAIVABLE, (
            f"{check_id} represents a potential document authenticity failure "
            "and cannot be waived."
        )

    if check_id == "UCP-001" and status == "failed":
        return NON_WAIVABLE, (
            "A missing required document cannot be waived — "
            "the document must be physically presented."
        )

    if check_id == "MATCH-002" and status == "failed":
        return NON_WAIVABLE, "Currency mismatch is a fundamental error that cannot be waived."

    # --- WAIVABLE_AUTO ---

    if check_id in _DATA_QUALITY_CHECKS:
        return WAIVABLE_AUTO, "Data quality or confidence warning — does not affect the compliance decision."

    waiver_policy = policy.get("waiver", {})
    auto_waive_data_quality = waiver_policy.get("auto_waive_data_quality", True)
    auto_waive_typos = policy.get("discrepancy", {}).get("auto_waive_trivial_typos", False)

    if severity == "minor" and auto_waive_data_quality and check_id.startswith("INPUT-"):
        return WAIVABLE_AUTO, "Minor input validation warning — auto-waived per policy."

    if severity == "minor" and auto_waive_typos and ("typo" in explanation or "format" in explanation):
        return WAIVABLE_AUTO, "Trivial typo or formatting issue — auto-waived per policy."

    if check_id == "FRD-004" and severity == "minor":
        return WAIVABLE_AUTO, "Minor date sequence observation — informational, not a compliance block."

    if severity == "minor":
        return WAIVABLE_AUTO, "Minor finding — below the threshold requiring applicant involvement."

    # --- WAIVABLE_NEEDS_APPLICANT ---

    rationale = _NEEDS_APPLICANT_RATIONALES.get(
        check_id,
        "Major finding — applicant waiver or manual review required before proceeding.",
    )
    return WAIVABLE_NEEDS_APPLICANT, rationale


def _load_all_findings(run_folder: Path) -> list[dict[str, Any]]:
    all_findings: list[dict[str, Any]] = []
    for source, filenames in _SOURCE_FILES:
        for filename in filenames:
            path = run_folder / filename
            if path.exists():
                data = _read_json(path)
                for finding in data.get("findings", []):
                    enriched = dict(finding)
                    if "source" not in enriched:
                        enriched["source"] = source
                    all_findings.append(enriched)
                break
    return all_findings


def run(run_folder: str | Path) -> dict[str, Any]:
    print("[Agent G] Discrepancy Waiver Classification Agent running...")

    run_folder = Path(run_folder)
    policy = _read_policy(settings.POLICIES_DIR / "policy_pack.yaml")

    context = _read_json(run_folder / "context.json") or _read_json(run_folder / "context_packet.json")
    case_id = context.get("manifest", {}).get("case_id") or run_folder.name

    all_findings = _load_all_findings(run_folder)

    classified: list[dict[str, Any]] = []
    waiver_index: dict[str, str] = {}
    counts = {NON_WAIVABLE: 0, WAIVABLE_NEEDS_APPLICANT: 0, WAIVABLE_AUTO: 0}

    for finding in all_findings:
        finding_id = finding.get("finding_id", "")
        waiver_status, waiver_rationale = _classify(finding, policy)

        classified.append({
            "finding_id": finding_id,
            "source": finding.get("source", "unknown"),
            "check_id": finding.get("check_id", ""),
            "severity": finding.get("severity", ""),
            "waiver_status": waiver_status,
            "waiver_rationale": waiver_rationale,
        })

        if finding_id:
            waiver_index[finding_id] = waiver_status
        counts[waiver_status] += 1

    result: dict[str, Any] = {
        "case_id": case_id,
        "summary": {
            "total_findings_reviewed": len(all_findings),
            NON_WAIVABLE: counts[NON_WAIVABLE],
            WAIVABLE_NEEDS_APPLICANT: counts[WAIVABLE_NEEDS_APPLICANT],
            WAIVABLE_AUTO: counts[WAIVABLE_AUTO],
        },
        "waiver_index": waiver_index,
        "classified_findings": classified,
    }

    output_path = run_folder / "waiver_result.json"
    _write_json(output_path, result)

    print("Agent G completed")
    print(f"waiver_result.json created at: {output_path}")
    print(
        f"NON_WAIVABLE: {counts[NON_WAIVABLE]}, "
        f"WAIVABLE_NEEDS_APPLICANT: {counts[WAIVABLE_NEEDS_APPLICANT]}, "
        f"WAIVABLE_AUTO: {counts[WAIVABLE_AUTO]}"
    )

    return result


if __name__ == "__main__":
    run("runs/run_001")

"""Agent H: Exception triage, final decision, and reporting."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from core.config import settings


SEVERITY_RANK = {
    "critical": 3,
    "major": 2,
    "minor": 1,
    "info": 0,
    "warning": 1,
}

INPUT_ARTIFACTS = {
    "ucp": ["ucp_result.json"],
    "matching": ["match_result.json"],
    "sanctions": ["sanctions_screen.json", "sanctions_result.json"],
}


# Main entry point used by the orchestrator.
def run(run_folder: str | Path) -> dict[str, Any]:
    run_folder = Path(run_folder)
    context = _read_json(run_folder / "context.json") or _read_json(run_folder / "context_packet.json")
    policy = _read_yaml(settings.POLICIES_DIR / "policy_pack.yaml")

    loaded_artifacts: dict[str, dict[str, Any]] = {}
    findings: list[dict[str, Any]] = []

    for source, filenames in INPUT_ARTIFACTS.items():
        artifact_path = _first_existing(run_folder, filenames)
        if artifact_path is None:
            findings.append(_missing_input_finding(source, filenames[0]))
            continue

        artifact = _read_json(artifact_path)
        loaded_artifacts[source] = artifact
        findings.extend(_normalize_findings(source, artifact.get("findings", [])))

    case_id = _case_id(context, loaded_artifacts, run_folder)
    findings = _dedupe_findings(findings)
    findings = sorted(findings, key=lambda item: _severity_rank(item.get("severity")), reverse=True)

    decision, processing_status, rationale = _make_decision(findings, policy)
    severity_counts = _count_severities(findings)
    swift_type = _swift_type(decision, policy)

    final_decision = {
        "run_id": run_folder.name,
        "case_id": case_id,
        "decided_at": datetime.now(timezone.utc).isoformat(),
        "decision": decision,
        "processing_status": processing_status,
        "decision_rationale": rationale,
        "swift_message_type": swift_type,
        "critical_discrepancy_count": severity_counts["critical"],
        "major_discrepancy_count": severity_counts["major"],
        "minor_discrepancy_count": severity_counts["minor"],
        "total_discrepancy_count": len(findings),
        "discrepancies": findings,
    }

    metrics = {
        "run_id": run_folder.name,
        "case_id": case_id,
        "generated_at": final_decision["decided_at"],
        "decision": decision,
        "processing_status": processing_status,
        "total_findings": len(findings),
        "critical_findings": severity_counts["critical"],
        "major_findings": severity_counts["major"],
        "minor_findings": severity_counts["minor"],
        "input_artifacts_loaded": sorted(loaded_artifacts.keys()),
        "input_artifacts_missing": sorted(set(INPUT_ARTIFACTS.keys()) - set(loaded_artifacts.keys())),
    }

    _write_json(run_folder / "final_decision.json", final_decision)
    _write_json(run_folder / "metrics.json", metrics)
    _write_text(run_folder / "discrepancies.md", _render_discrepancies(case_id, final_decision))
    _write_text(run_folder / "swift_draft.txt", _render_swift_draft(case_id, final_decision))
    _write_text(run_folder / "audit_log.md", _render_audit_log(case_id, final_decision, metrics))

    print("Agent H completed")
    print(f"final_decision.json created at: {run_folder / 'final_decision.json'}")
    print(f"Decision: {decision} ({processing_status})")

    return final_decision


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return {}


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _first_existing(run_folder: Path, filenames: list[str]) -> Path | None:
    for filename in filenames:
        candidate = run_folder / filename
        if candidate.exists():
            return candidate
    return None


def _case_id(context: dict[str, Any], artifacts: dict[str, dict[str, Any]], run_folder: Path) -> str:
    manifest = context.get("manifest", {}) if context else {}
    if manifest.get("case_id"):
        return str(manifest["case_id"])
    if context.get("case_id"):
        return str(context["case_id"])
    for artifact in artifacts.values():
        if artifact.get("case_id"):
            return str(artifact["case_id"])
    return run_folder.name


def _normalize_findings(source: str, raw_findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for index, finding in enumerate(raw_findings, start=1):
        severity = str(finding.get("severity") or "minor").lower()
        if severity == "warning":
            severity = "minor"
        if severity not in {"critical", "major", "minor", "info"}:
            severity = "minor"

        normalized.append(
            {
                "finding_id": finding.get("finding_id") or f"H-{source.upper()}-{index:03}",
                "source": source,
                "agent_name": finding.get("agent_name") or source,
                "check_id": finding.get("check_id") or "UNKNOWN",
                "severity": severity,
                "status": finding.get("status") or "warning",
                "document": finding.get("document") or "unknown",
                "field": finding.get("field") or "unknown",
                "expected_value": finding.get("expected_value"),
                "actual_value": finding.get("actual_value"),
                "explanation": finding.get("explanation") or "No explanation provided.",
                "evidence": finding.get("evidence") or [],
                "policy_reference": finding.get("policy_reference") or "UNSPECIFIED",
                "waivable": _is_waivable(severity, finding),
            }
        )
    return normalized


def _missing_input_finding(source: str, filename: str) -> dict[str, Any]:
    return {
        "finding_id": f"H-MISSING-{source.upper()}",
        "source": "triage",
        "agent_name": "Agent H - Triage",
        "check_id": "INPUT-001",
        "severity": "minor",
        "status": "warning",
        "document": filename,
        "field": "file",
        "expected_value": "present",
        "actual_value": "missing",
        "explanation": f"Agent H could not find {filename}; final decision requires manual review.",
        "evidence": [],
        "policy_reference": "INPUT_VALIDATION",
        "waivable": False,
    }


def _dedupe_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: dict[tuple[Any, ...], dict[str, Any]] = {}
    for finding in findings:
        key = (
            finding.get("source"),
            finding.get("check_id"),
            finding.get("document"),
            finding.get("field"),
            finding.get("explanation"),
        )
        existing = deduped.get(key)
        if existing is None or _severity_rank(finding.get("severity")) > _severity_rank(existing.get("severity")):
            deduped[key] = finding
    return list(deduped.values())


def _severity_rank(severity: Any) -> int:
    return SEVERITY_RANK.get(str(severity).lower(), 0)


def _count_severities(findings: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"critical": 0, "major": 0, "minor": 0}
    for finding in findings:
        severity = str(finding.get("severity") or "minor").lower()
        if severity in counts:
            counts[severity] += 1
        elif severity == "info":
            continue
        else:
            counts["minor"] += 1
    return counts


def _make_decision(findings: list[dict[str, Any]], policy: dict[str, Any]) -> tuple[str, str, str]:
    counts = _count_severities(findings)
    discrepancy_policy = policy.get("discrepancy", {})
    sanctions_policy = policy.get("sanctions", {})

    if counts["critical"] > 0:
        if sanctions_policy.get("freeze_on_hit", True):
            return "MANUAL_REVIEW", "HOLD", "Critical sanctions or blocking finding detected; processing is frozen for review."
        return "REFUSE", "STOPPED", "Critical finding detected."

    if counts["major"] > 0:
        if discrepancy_policy.get("major_auto_refuse", True):
            return "REFUSE", "STOPPED", "Major discrepancies detected; presentation should be refused."
        return "MANUAL_REVIEW", "REVIEW_REQUIRED", "Major discrepancies require manual review."

    if counts["minor"] > 0:
        if discrepancy_policy.get("minor_manual_review", True):
            return "MANUAL_REVIEW", "REVIEW_REQUIRED", "Minor discrepancies or missing inputs require manual review."

    return "HONOUR", "CLEAR", "No blocking discrepancies were detected."


def _swift_type(decision: str, policy: dict[str, Any]) -> str:
    routing = policy.get("routing", {})
    if decision == "HONOUR":
        return routing.get("honour_swift_type", "MT752")
    if decision == "REFUSE":
        return routing.get("refuse_swift_type", "MT734")
    return routing.get("manual_review_swift_type", "MT752")


def _is_waivable(severity: str, finding: dict[str, Any]) -> bool:
    if severity in {"critical", "major"}:
        return False
    text = f"{finding.get('field', '')} {finding.get('explanation', '')}".lower()
    return "typo" in text or "format" in text


def _render_discrepancies(case_id: str, final_decision: dict[str, Any]) -> str:
    lines = [
        "# Discrepancies",
        "",
        f"Case ID: {case_id}",
        f"Decision: {final_decision['decision']}",
        f"Processing status: {final_decision['processing_status']}",
        f"Rationale: {final_decision['decision_rationale']}",
        "",
        "## Findings",
    ]
    if not final_decision["discrepancies"]:
        lines.append("- No discrepancies found.")
    for finding in final_decision["discrepancies"]:
        lines.append(
            f"- [{finding['severity'].upper()}] {finding['finding_id']} "
            f"({finding['source']} / {finding['document']} / {finding['field']}): "
            f"{finding['explanation']}"
        )
    return "\n".join(lines) + "\n"


def _render_swift_draft(case_id: str, final_decision: dict[str, Any]) -> str:
    swift_type = final_decision["swift_message_type"]
    decision = final_decision["decision"]
    lines = [
        f"SWIFT DRAFT - {swift_type}",
        f"CASE: {case_id}",
        f"DECISION: {decision}",
        f"PROCESSING STATUS: {final_decision['processing_status']}",
        "",
        "NARRATIVE:",
        final_decision["decision_rationale"],
    ]
    if final_decision["discrepancies"]:
        lines.extend(["", "DISCREPANCIES:"])
        for finding in final_decision["discrepancies"]:
            lines.append(f"- {finding['severity'].upper()}: {finding['explanation']}")
    return "\n".join(lines) + "\n"


def _render_audit_log(case_id: str, final_decision: dict[str, Any], metrics: dict[str, Any]) -> str:
    lines = [
        "# Audit Log",
        "",
        f"Case ID: {case_id}",
        f"Run ID: {final_decision['run_id']}",
        f"Decision timestamp: {final_decision['decided_at']}",
        f"Decision: {final_decision['decision']}",
        f"Processing status: {final_decision['processing_status']}",
        "",
        "## Loaded Inputs",
    ]
    for source in metrics["input_artifacts_loaded"]:
        lines.append(f"- {source}: loaded")
    for source in metrics["input_artifacts_missing"]:
        lines.append(f"- {source}: missing")
    lines.extend([
        "",
        "## Finding Counts",
        f"- Critical: {metrics['critical_findings']}",
        f"- Major: {metrics['major_findings']}",
        f"- Minor: {metrics['minor_findings']}",
    ])
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    run("runs/run_001")
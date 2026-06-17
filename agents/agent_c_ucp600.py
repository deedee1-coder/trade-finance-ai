import json
from datetime import datetime
from pathlib import Path
from typing import Any


AGENT_NAME = "Agent C - UCP Compliance"

DEFAULT_POLICY = {
    "required_documents": [
        "commercial_invoice",
        "bill_of_lading",
        "packing_list",
        "certificate_of_origin",
    ],
    "presentation_period_days": 21,
    "low_confidence_threshold": 0.75,
    "severity": {
        "missing_document": "major",
        "late_shipment": "major",
        "late_presentation": "major",
        "low_confidence": "minor",
        "invalid_field": "minor",
    },
}


def read_json_file(file_path: Path) -> dict[str, Any]:
    if not file_path.exists():
        return {}

    try:
        with file_path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError:
        return {}


def write_json_file(file_path: Path, data: dict[str, Any]) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with file_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)


def read_policy_file(policy_path: Path) -> dict[str, Any]:
    policy = DEFAULT_POLICY.copy()

    if not policy_path.exists():
        return policy

    try:
        import yaml

        with policy_path.open("r", encoding="utf-8") as file:
            loaded_policy = yaml.safe_load(file) or {}

        policy.update(loaded_policy)
        policy["severity"] = {
            **DEFAULT_POLICY["severity"],
            **loaded_policy.get("severity", {}),
        }

    except Exception:
        return policy

    return policy


def parse_date(value: Any) -> datetime | None:
    if not value:
        return None

    try:
        return datetime.strptime(str(value), "%Y-%m-%d")
    except ValueError:
        return None


def build_finding(
    finding_id: str,
    check_id: str,
    severity: str,
    status: str,
    document: str,
    field: str,
    expected_value: Any,
    actual_value: Any,
    explanation: str,
    policy_reference: str,
    evidence: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "finding_id": finding_id,
        "agent_name": AGENT_NAME,
        "check_id": check_id,
        "severity": severity,
        "status": status,
        "document": document,
        "field": field,
        "expected_value": expected_value,
        "actual_value": actual_value,
        "explanation": explanation,
        "evidence": evidence or [],
        "policy_reference": policy_reference,
    }


def get_case_id(
    run_folder: Path,
    context: dict[str, Any],
    extracted_fields: dict[str, Any],
    case_metadata: dict[str, Any],
) -> str:
    return (
        case_metadata.get("case_id")
        or context.get("case_id")
        or extracted_fields.get("case_id")
        or run_folder.name
    )


def get_present_document_types(context: dict[str, Any]) -> list[str]:
    documents = context.get("documents", [])
    document_types = []

    for document in documents:
        if isinstance(document, dict):
            if document.get("present") is False:
                continue

            document_type = document.get("document_type")

            if document_type:
                document_types.append(str(document_type))

    return document_types


def check_required_documents(
    case_id: str,
    context: dict[str, Any],
    policy: dict[str, Any],
) -> list[dict[str, Any]]:
    findings = []

    required_documents = policy.get(
        "required_documents",
        DEFAULT_POLICY["required_documents"],
    )

    present_documents = get_present_document_types(context)

    for index, required_document in enumerate(required_documents, start=1):
        if required_document not in present_documents:
            findings.append(
                build_finding(
                    finding_id=f"C-{case_id}-REQDOC-{index:03}",
                    check_id="UCP-001",
                    severity=policy["severity"]["missing_document"],
                    status="failed",
                    document=str(required_document),
                    field="document_presence",
                    expected_value="present",
                    actual_value="missing",
                    explanation=(
                        f"Required document '{required_document}' is missing "
                        "from the document bundle."
                    ),
                    policy_reference="UCP600_REQUIRED_DOCUMENTS",
                )
            )

    return findings


def check_latest_shipment_date(
    case_id: str,
    extracted_fields: dict[str, Any],
    policy: dict[str, Any],
) -> list[dict[str, Any]]:
    findings = []

    shipment_date_raw = extracted_fields.get("shipment_date")
    latest_shipment_date_raw = extracted_fields.get("latest_shipment_date")

    shipment_date = parse_date(shipment_date_raw)
    latest_shipment_date = parse_date(latest_shipment_date_raw)

    if shipment_date is None:
        findings.append(
            build_finding(
                finding_id=f"C-{case_id}-SHIP-001",
                check_id="UCP-002",
                severity=policy["severity"]["invalid_field"],
                status="warning",
                document="transport_document",
                field="shipment_date",
                expected_value="valid YYYY-MM-DD shipment date",
                actual_value=shipment_date_raw,
                explanation=(
                    "Shipment date is missing or invalid, so the latest shipment "
                    "date check could not be fully completed."
                ),
                policy_reference="UCP600_LATEST_SHIPMENT_DATE",
            )
        )

    if latest_shipment_date is None:
        findings.append(
            build_finding(
                finding_id=f"C-{case_id}-SHIP-002",
                check_id="UCP-002",
                severity=policy["severity"]["invalid_field"],
                status="warning",
                document="letter_of_credit",
                field="latest_shipment_date",
                expected_value="valid YYYY-MM-DD latest shipment date",
                actual_value=latest_shipment_date_raw,
                explanation=(
                    "Latest shipment date is missing or invalid, so the latest "
                    "shipment date check could not be fully completed."
                ),
                policy_reference="UCP600_LATEST_SHIPMENT_DATE",
            )
        )

    if shipment_date is None or latest_shipment_date is None:
        return findings

    if shipment_date > latest_shipment_date:
        findings.append(
            build_finding(
                finding_id=f"C-{case_id}-SHIP-003",
                check_id="UCP-002",
                severity=policy["severity"]["late_shipment"],
                status="failed",
                document="transport_document",
                field="shipment_date",
                expected_value=str(latest_shipment_date.date()),
                actual_value=str(shipment_date.date()),
                explanation=(
                    f"Shipment date {shipment_date.date()} is after the latest "
                    f"shipment date {latest_shipment_date.date()} allowed by the "
                    "Letter of Credit."
                ),
                policy_reference="UCP600_LATEST_SHIPMENT_DATE",
            )
        )

    return findings


def check_presentation_period(
    case_id: str,
    extracted_fields: dict[str, Any],
    case_metadata: dict[str, Any],
    policy: dict[str, Any],
) -> list[dict[str, Any]]:
    findings = []

    shipment_date_raw = extracted_fields.get("shipment_date")
    presentation_date_raw = case_metadata.get("presentation_date")

    shipment_date = parse_date(shipment_date_raw)
    presentation_date = parse_date(presentation_date_raw)

    presentation_period_raw = (
        extracted_fields.get("presentation_rule_days")
        or extracted_fields.get("presentation_period_days")
        or policy.get("presentation_period_days")
    )

    if shipment_date is None:
        findings.append(
            build_finding(
                finding_id=f"C-{case_id}-PRES-001",
                check_id="UCP-003",
                severity=policy["severity"]["invalid_field"],
                status="warning",
                document="transport_document",
                field="shipment_date",
                expected_value="valid YYYY-MM-DD shipment date",
                actual_value=shipment_date_raw,
                explanation=(
                    "Shipment date is missing or invalid, so the presentation "
                    "period check could not be fully completed."
                ),
                policy_reference="UCP600_PRESENTATION_PERIOD",
            )
        )

    if presentation_date is None:
        findings.append(
            build_finding(
                finding_id=f"C-{case_id}-PRES-002",
                check_id="UCP-003",
                severity=policy["severity"]["invalid_field"],
                status="warning",
                document="case_metadata",
                field="presentation_date",
                expected_value="valid YYYY-MM-DD presentation date",
                actual_value=presentation_date_raw,
                explanation=(
                    "Presentation date is missing or invalid, so the presentation "
                    "period check could not be fully completed."
                ),
                policy_reference="UCP600_PRESENTATION_PERIOD",
            )
        )

    try:
        presentation_period_days = int(str(presentation_period_raw))
    except (TypeError, ValueError):
        findings.append(
            build_finding(
                finding_id=f"C-{case_id}-PRES-003",
                check_id="UCP-003",
                severity=policy["severity"]["invalid_field"],
                status="warning",
                document="letter_of_credit",
                field="presentation_period_days",
                expected_value="integer number of allowed presentation days",
                actual_value=presentation_period_raw,
                explanation=(
                    "Presentation period days is missing or invalid, so the "
                    "presentation period check could not be fully completed."
                ),
                policy_reference="UCP600_PRESENTATION_PERIOD",
            )
        )

        return findings

    if shipment_date is None or presentation_date is None:
        return findings

    days_after_shipment = (presentation_date - shipment_date).days

    if days_after_shipment > presentation_period_days:
        findings.append(
            build_finding(
                finding_id=f"C-{case_id}-PRES-004",
                check_id="UCP-003",
                severity=policy["severity"]["late_presentation"],
                status="failed",
                document="case_metadata",
                field="presentation_date",
                expected_value=f"within {presentation_period_days} days after shipment",
                actual_value=f"{days_after_shipment} days after shipment",
                explanation=(
                    f"Presentation is {days_after_shipment} days after shipment, "
                    f"exceeding the allowed {presentation_period_days}-day rule."
                ),
                policy_reference="UCP600_PRESENTATION_PERIOD",
            )
        )

    return findings


def check_low_confidence_fields(
    case_id: str,
    extracted_fields: dict[str, Any],
    policy: dict[str, Any],
) -> list[dict[str, Any]]:
    findings = []
    threshold = float(policy.get("low_confidence_threshold", 0.75))
    counter = 1

    def scan_value(path: str, value: Any) -> None:
        nonlocal counter

        if isinstance(value, dict):
            confidence = value.get("confidence")

            if isinstance(confidence, (int, float)) and confidence < threshold:
                findings.append(
                    build_finding(
                        finding_id=f"C-{case_id}-CONF-{counter:03}",
                        check_id="UCP-004",
                        severity=policy["severity"]["low_confidence"],
                        status="warning",
                        document=path.split(".")[0],
                        field=path,
                        expected_value=f"confidence >= {threshold}",
                        actual_value=confidence,
                        explanation=(
                            f"Field '{path}' has low extraction confidence "
                            f"({confidence}). Manual review is recommended."
                        ),
                        evidence=[
                            {
                                "document": path.split(".")[0],
                                "field": path,
                                "source": "extracted_fields.json",
                                "page": value.get("page"),
                                "source_text": value.get("source_text"),
                                "confidence": confidence,
                            }
                        ],
                        policy_reference="LOW_CONFIDENCE_THRESHOLD",
                    )
                )

                counter += 1

            for child_key, child_value in value.items():
                scan_value(f"{path}.{child_key}", child_value)

        elif isinstance(value, list):
            for index, item in enumerate(value):
                scan_value(f"{path}[{index}]", item)

    for key, value in extracted_fields.items():
        scan_value(key, value)

    return findings


def find_extracted_fields_file(run_folder: Path) -> Path:
    primary_path = run_folder / "extracted_fields.json"

    if primary_path.exists():
        return primary_path

    return Path("data") / "sample_documents" / "case_001_clean" / "extracted_fields.json"


def run(run_folder: str | Path) -> dict[str, Any]:
    run_folder = Path(run_folder)

    context_path = run_folder / "context.json"
    extracted_fields_path = find_extracted_fields_file(run_folder)
    case_metadata_path = run_folder / "case_metadata.json"
    policy_path = Path("policies") / "policy_pack.yaml"

    context = read_json_file(context_path)
    extracted_fields = read_json_file(extracted_fields_path)
    case_metadata = read_json_file(case_metadata_path)
    policy = read_policy_file(policy_path)

    case_id = get_case_id(
        run_folder=run_folder,
        context=context,
        extracted_fields=extracted_fields,
        case_metadata=case_metadata,
    )

    findings = []

    if not context:
        findings.append(
            build_finding(
                finding_id=f"C-{case_id}-INPUT-001",
                check_id="INPUT-001",
                severity=policy["severity"]["invalid_field"],
                status="warning",
                document="context.json",
                field="file",
                expected_value="valid context.json",
                actual_value="missing_or_invalid",
                explanation=f"context.json is missing or invalid at: {context_path}",
                policy_reference="INPUT_VALIDATION",
            )
        )

    if not extracted_fields:
        findings.append(
            build_finding(
                finding_id=f"C-{case_id}-INPUT-002",
                check_id="INPUT-002",
                severity=policy["severity"]["invalid_field"],
                status="warning",
                document="extracted_fields.json",
                field="file",
                expected_value="valid extracted_fields.json",
                actual_value="missing_or_invalid",
                explanation=(
                    f"extracted_fields.json is missing or invalid at: "
                    f"{extracted_fields_path}"
                ),
                policy_reference="INPUT_VALIDATION",
            )
        )

    if not case_metadata:
        findings.append(
            build_finding(
                finding_id=f"C-{case_id}-INPUT-003",
                check_id="INPUT-003",
                severity=policy["severity"]["invalid_field"],
                status="warning",
                document="case_metadata.json",
                field="file",
                expected_value="valid case_metadata.json",
                actual_value="missing_or_invalid",
                explanation=f"case_metadata.json is missing or invalid at: {case_metadata_path}",
                policy_reference="INPUT_VALIDATION",
            )
        )

    findings.extend(check_required_documents(case_id, context, policy))
    findings.extend(check_latest_shipment_date(case_id, extracted_fields, policy))
    findings.extend(
        check_presentation_period(
            case_id=case_id,
            extracted_fields=extracted_fields,
            case_metadata=case_metadata,
            policy=policy,
        )
    )
    findings.extend(check_low_confidence_fields(case_id, extracted_fields, policy))

    result = {
        "case_id": case_id,
        "findings": findings,
    }

    output_path = run_folder / "ucp_result.json"
    write_json_file(output_path, result)

    print("Agent C completed")
    print(f"ucp_result.json created at: {output_path}")
    print(f"Findings created: {len(findings)}")

    return result


if __name__ == "__main__":
    output = run("runs/run_001")

    print()
    print("Summary")
    print("-" * 40)
    print("Case:", output["case_id"])
    print("Findings:", len(output["findings"]))

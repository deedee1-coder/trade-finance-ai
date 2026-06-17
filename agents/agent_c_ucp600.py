import json
from datetime import datetime
from pathlib import Path
from typing import Any


REQUIRED_DOCUMENTS = [
    "commercial_invoice",
    "bill_of_lading",
    "packing_list",
    "certificate_of_origin",
]


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


def parse_date(date_value: str | None) -> datetime | None:
    if not date_value:
        return None

    try:
        return datetime.strptime(date_value, "%Y-%m-%d")
    except ValueError:
        return None


def get_present_document_types(context: dict[str, Any]) -> list[str]:
    documents = context.get("documents", [])
    present_document_types = []

    for document in documents:
        document_type = document.get("document_type")

        if document_type:
            present_document_types.append(document_type)

    return present_document_types


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
) -> dict[str, Any]:
    return {
        "finding_id": finding_id,
        "agent_name": "Agent C - UCP Compliance",
        "check_id": check_id,
        "severity": severity,
        "status": status,
        "document": document,
        "field": field,
        "expected_value": expected_value,
        "actual_value": actual_value,
        "explanation": explanation,
        "evidence": [],
        "policy_reference": policy_reference,
    }


def check_required_documents(
    case_id: str,
    context: dict[str, Any],
) -> list[dict[str, Any]]:
    findings = []

    present_documents = get_present_document_types(context)

    missing_documents = [
        required_document
        for required_document in REQUIRED_DOCUMENTS
        if required_document not in present_documents
    ]

    for index, missing_document in enumerate(missing_documents, start=1):
        findings.append(
            build_finding(
                finding_id=f"C-{case_id}-REQDOC-{index:03}",
                check_id="UCP-001",
                severity="major",
                status="fail",
                document=missing_document,
                field="document_presence",
                expected_value="present",
                actual_value="missing",
                explanation=f"Required document '{missing_document}' is missing from the document bundle.",
                policy_reference="UCP600_REQUIRED_DOCUMENTS",
            )
        )

    return findings


def check_latest_shipment_date(
    case_id: str,
    extracted_fields: dict[str, Any],
) -> list[dict[str, Any]]:
    findings = []

    shipment_date = parse_date(extracted_fields.get("shipment_date"))
    latest_shipment_date = parse_date(extracted_fields.get("latest_shipment_date"))

    if shipment_date is None:
        findings.append(
            build_finding(
                finding_id=f"C-{case_id}-SHIP-001",
                check_id="UCP-002",
                severity="minor",
                status="error",
                document="transport_document",
                field="shipment_date",
                expected_value="valid YYYY-MM-DD shipment date",
                actual_value=extracted_fields.get("shipment_date"),
                explanation="Shipment date is missing or invalid, so the latest shipment date check could not be completed.",
                policy_reference="UCP600_LATEST_SHIPMENT_DATE",
            )
        )

    if latest_shipment_date is None:
        findings.append(
            build_finding(
                finding_id=f"C-{case_id}-SHIP-002",
                check_id="UCP-002",
                severity="minor",
                status="error",
                document="letter_of_credit",
                field="latest_shipment_date",
                expected_value="valid YYYY-MM-DD latest shipment date",
                actual_value=extracted_fields.get("latest_shipment_date"),
                explanation="Latest shipment date is missing or invalid, so the latest shipment date check could not be completed.",
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
                severity="major",
                status="fail",
                document="transport_document",
                field="shipment_date",
                expected_value=str(latest_shipment_date.date()),
                actual_value=str(shipment_date.date()),
                explanation=(
                    f"Shipment date {shipment_date.date()} is after the latest shipment date "
                    f"{latest_shipment_date.date()} allowed by the Letter of Credit."
                ),
                policy_reference="UCP600_LATEST_SHIPMENT_DATE",
            )
        )

    return findings


def check_presentation_period(
    case_id: str,
    extracted_fields: dict[str, Any],
    case_metadata: dict[str, Any],
) -> list[dict[str, Any]]:
    findings = []

    shipment_date = parse_date(extracted_fields.get("shipment_date"))
    presentation_date = parse_date(case_metadata.get("presentation_date"))
    presentation_rule_days = extracted_fields.get("presentation_rule_days")

    if shipment_date is None:
        findings.append(
            build_finding(
                finding_id=f"C-{case_id}-PRES-001",
                check_id="UCP-003",
                severity="minor",
                status="error",
                document="transport_document",
                field="shipment_date",
                expected_value="valid YYYY-MM-DD shipment date",
                actual_value=extracted_fields.get("shipment_date"),
                explanation="Shipment date is missing or invalid, so the presentation period check could not be completed.",
                policy_reference="UCP600_PRESENTATION_PERIOD",
            )
        )

    if presentation_date is None:
        findings.append(
            build_finding(
                finding_id=f"C-{case_id}-PRES-002",
                check_id="UCP-003",
                severity="minor",
                status="error",
                document="case_metadata",
                field="presentation_date",
                expected_value="valid YYYY-MM-DD presentation date",
                actual_value=case_metadata.get("presentation_date"),
                explanation="Presentation date is missing or invalid, so the presentation period check could not be completed.",
                policy_reference="UCP600_PRESENTATION_PERIOD",
            )
        )

    try:
        presentation_rule_days = int(presentation_rule_days)
    except (TypeError, ValueError):
        findings.append(
            build_finding(
                finding_id=f"C-{case_id}-PRES-003",
                check_id="UCP-003",
                severity="minor",
                status="error",
                document="letter_of_credit",
                field="presentation_rule_days",
                expected_value="integer number of allowed presentation days",
                actual_value=extracted_fields.get("presentation_rule_days"),
                explanation="Presentation rule days is missing or invalid, so the presentation period check could not be completed.",
                policy_reference="UCP600_PRESENTATION_PERIOD",
            )
        )
        return findings

    if shipment_date is None or presentation_date is None:
        return findings

    days_after_shipment = (presentation_date - shipment_date).days

    if days_after_shipment > presentation_rule_days:
        findings.append(
            build_finding(
                finding_id=f"C-{case_id}-PRES-004",
                check_id="UCP-003",
                severity="major",
                status="fail",
                document="case_metadata",
                field="presentation_date",
                expected_value=f"within {presentation_rule_days} days after shipment",
                actual_value=f"{days_after_shipment} days after shipment",
                explanation=(
                    f"Presentation is {days_after_shipment} days after shipment, "
                    f"exceeding the allowed {presentation_rule_days}-day rule."
                ),
                policy_reference="UCP600_PRESENTATION_PERIOD",
            )
        )

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

    context = read_json_file(context_path)
    extracted_fields = read_json_file(extracted_fields_path)
    case_metadata = read_json_file(case_metadata_path)

    case_id = (
        case_metadata.get("case_id")
        or context.get("case_id")
        or extracted_fields.get("case_id")
        or run_folder.name
    )

    findings = []

    if not context:
        findings.append(
            build_finding(
                finding_id=f"C-{case_id}-INPUT-001",
                check_id="INPUT-001",
                severity="minor",
                status="error",
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
                severity="minor",
                status="error",
                document="extracted_fields.json",
                field="file",
                expected_value="valid extracted_fields.json",
                actual_value="missing_or_invalid",
                explanation=f"extracted_fields.json is missing or invalid at: {extracted_fields_path}",
                policy_reference="INPUT_VALIDATION",
            )
        )

    if not case_metadata:
        findings.append(
            build_finding(
                finding_id=f"C-{case_id}-INPUT-003",
                check_id="INPUT-003",
                severity="minor",
                status="error",
                document="case_metadata.json",
                field="file",
                expected_value="valid case_metadata.json",
                actual_value="missing_or_invalid",
                explanation=f"case_metadata.json is missing or invalid at: {case_metadata_path}",
                policy_reference="INPUT_VALIDATION",
            )
        )

    findings.extend(check_required_documents(case_id, context))
    findings.extend(check_latest_shipment_date(case_id, extracted_fields))
    findings.extend(check_presentation_period(case_id, extracted_fields, case_metadata))

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
    result = run("runs/run_001")

    print()
    print("Summary")
    print("-" * 40)
    print("Case:", result["case_id"])
    print("Findings:", len(result["findings"]))
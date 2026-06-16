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
    """
    Safely read a JSON file.
    If the file does not exist or is invalid, return an empty dictionary.
    """
    if not file_path.exists():
        return {}

    try:
        with file_path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError:
        return {}


def write_json_file(file_path: Path, data: dict[str, Any]) -> None:
    """
    Write dictionary data to a JSON file.
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with file_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)


def parse_date(date_value: str | None) -> datetime | None:
    """
    Convert YYYY-MM-DD string into a datetime object.
    Returns None if the value is missing or invalid.
    """
    if not date_value:
        return None

    try:
        return datetime.strptime(date_value, "%Y-%m-%d")
    except ValueError:
        return None


def get_present_document_types(context: dict[str, Any]) -> list[str]:
    """
    Extract document types from context.json.

    Supports formats like:
    {
      "documents": [
        {"document_type": "commercial_invoice"}
      ]
    }
    """
    documents = context.get("documents", [])

    present_document_types = []

    for document in documents:
        document_type = document.get("document_type")

        if document_type:
            present_document_types.append(document_type)

    return present_document_types


def build_check(
    rule_id: str,
    rule_name: str,
    result: str,
    severity: str,
    description: str,
) -> dict[str, str]:
    """
    Standard structure for one UCP compliance check.
    """
    return {
        "rule_id": rule_id,
        "rule_name": rule_name,
        "result": result,
        "severity": severity,
        "description": description,
    }


def build_discrepancy(
    discrepancy_type: str,
    severity: str,
    description: str,
) -> dict[str, str]:
    """
    Standard structure for one discrepancy/finding.
    """
    return {
        "type": discrepancy_type,
        "severity": severity,
        "description": description,
    }


def check_required_documents(context: dict[str, Any]) -> tuple[dict[str, str], list[dict[str, str]]]:
    """
    Check 1:
    Verify all required LC documents are present.
    """
    present_documents = get_present_document_types(context)

    missing_documents = [
        required_document
        for required_document in REQUIRED_DOCUMENTS
        if required_document not in present_documents
    ]

    if not missing_documents:
        check = build_check(
            rule_id="UCP-001",
            rule_name="Required Documents Check",
            result="pass",
            severity="none",
            description="All required documents are present.",
        )

        return check, []

    description = (
        "Missing required document(s): "
        + ", ".join(missing_documents)
        + "."
    )

    check = build_check(
        rule_id="UCP-001",
        rule_name="Required Documents Check",
        result="fail",
        severity="high",
        description=description,
    )

    discrepancies = [
        build_discrepancy(
            discrepancy_type="missing_required_document",
            severity="high",
            description=description,
        )
    ]

    return check, discrepancies


def check_latest_shipment_date(
    extracted_fields: dict[str, Any]
) -> tuple[dict[str, str], list[dict[str, str]], list[str]]:
    """
    Check 2:
    Verify shipment_date <= latest_shipment_date.
    """
    errors = []

    shipment_date = parse_date(extracted_fields.get("shipment_date"))
    latest_shipment_date = parse_date(extracted_fields.get("latest_shipment_date"))

    if shipment_date is None:
        errors.append("Missing or invalid shipment_date.")
    if latest_shipment_date is None:
        errors.append("Missing or invalid latest_shipment_date.")

    if errors:
        check = build_check(
            rule_id="UCP-002",
            rule_name="Latest Shipment Date Check",
            result="error",
            severity="medium",
            description="Could not complete latest shipment date check.",
        )
        return check, [], errors

    if shipment_date <= latest_shipment_date:
        check = build_check(
            rule_id="UCP-002",
            rule_name="Latest Shipment Date Check",
            result="pass",
            severity="none",
            description="Shipment date is within the latest shipment date allowed by the Letter of Credit.",
        )
        return check, [], []

    description = (
        f"Shipment date {shipment_date.date()} is after latest shipment date "
        f"{latest_shipment_date.date()}."
    )

    check = build_check(
        rule_id="UCP-002",
        rule_name="Latest Shipment Date Check",
        result="fail",
        severity="high",
        description=description,
    )

    discrepancies = [
        build_discrepancy(
            discrepancy_type="late_shipment",
            severity="high",
            description=description,
        )
    ]

    return check, discrepancies, []


def check_presentation_period(
    extracted_fields: dict[str, Any],
    case_metadata: dict[str, Any],
) -> tuple[dict[str, str], list[dict[str, str]], list[str]]:
    """
    Check 3:
    Verify presentation_date - shipment_date <= presentation_rule_days.
    """
    errors = []

    shipment_date = parse_date(extracted_fields.get("shipment_date"))
    presentation_date = parse_date(case_metadata.get("presentation_date"))

    presentation_rule_days = extracted_fields.get("presentation_rule_days")

    if shipment_date is None:
        errors.append("Missing or invalid shipment_date.")
    if presentation_date is None:
        errors.append("Missing or invalid presentation_date.")
    if presentation_rule_days is None:
        errors.append("Missing presentation_rule_days.")

    try:
        presentation_rule_days = int(presentation_rule_days)
    except (TypeError, ValueError):
        errors.append("Invalid presentation_rule_days.")

    if errors:
        check = build_check(
            rule_id="UCP-003",
            rule_name="Presentation Period Check",
            result="error",
            severity="medium",
            description="Could not complete presentation period check.",
        )
        return check, [], errors

    days_after_shipment = (presentation_date - shipment_date).days

    if days_after_shipment <= presentation_rule_days:
        check = build_check(
            rule_id="UCP-003",
            rule_name="Presentation Period Check",
            result="pass",
            severity="none",
            description=(
                f"Documents were presented within {presentation_rule_days} days "
                "after shipment date."
            ),
        )
        return check, [], []

    description = (
        f"Presentation is {days_after_shipment} days after shipment, "
        f"exceeding the allowed {presentation_rule_days}-day rule."
    )

    check = build_check(
        rule_id="UCP-003",
        rule_name="Presentation Period Check",
        result="fail",
        severity="high",
        description=description,
    )

    discrepancies = [
        build_discrepancy(
            discrepancy_type="late_presentation",
            severity="high",
            description=description,
        )
    ]

    return check, discrepancies, []


def find_extracted_fields_file(run_folder: Path) -> Path:
    """
    Primary location:
      runs/run_001/extracted_fields.json

    Fallback location:
      data/sample_documents/case_001_clean/extracted_fields.json
    """
    primary_path = run_folder / "extracted_fields.json"

    if primary_path.exists():
        return primary_path

    fallback_path = Path("data") / "sample_documents" / "case_001_clean" / "extracted_fields.json"

    return fallback_path


def run(run_folder: str | Path) -> dict[str, Any]:
    """
    Main entry point for Agent C.

    Reads:
      - context.json
      - extracted_fields.json
      - case_metadata.json

    Writes:
      - ucp_result.json
    """
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
        or run_folder.name
    )

    checks = []
    discrepancies = []
    errors = []

    if not context:
        errors.append(f"context.json missing or invalid at: {context_path}")

    if not extracted_fields:
        errors.append(f"extracted_fields.json missing or invalid at: {extracted_fields_path}")

    if not case_metadata:
        errors.append(f"case_metadata.json missing or invalid at: {case_metadata_path}")

    required_documents_check, required_documents_discrepancies = check_required_documents(context)
    checks.append(required_documents_check)
    discrepancies.extend(required_documents_discrepancies)

    shipment_check, shipment_discrepancies, shipment_errors = check_latest_shipment_date(
        extracted_fields
    )
    checks.append(shipment_check)
    discrepancies.extend(shipment_discrepancies)
    errors.extend(shipment_errors)

    presentation_check, presentation_discrepancies, presentation_errors = check_presentation_period(
        extracted_fields,
        case_metadata,
    )
    checks.append(presentation_check)
    discrepancies.extend(presentation_discrepancies)
    errors.extend(presentation_errors)

    status = "success"

    if errors:
        status = "completed_with_errors"

    result = {
        "case_id": case_id,
        "agent_name": "Agent C - UCP Compliance",
        "status": status,
        "checks": checks,
        "discrepancies": discrepancies,
        "errors": errors,
    }

    output_path = run_folder / "ucp_result.json"
    write_json_file(output_path, result)

    print("Agent C completed")
    print(f"ucp_result.json created at: {output_path}")

    return result


if __name__ == "__main__":
    result = run("runs/run_001")

    print()
    print("Summary")
    print("-" * 40)
    print("Case:", result["case_id"])
    print("Status:", result["status"])
    print("Discrepancies:", len(result["discrepancies"]))
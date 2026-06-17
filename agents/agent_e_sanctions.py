import json
from pathlib import Path
from typing import Any


SANCTIONS_LIST_PATH = (
    Path("data")
    / "sanctions_lists"
    / "sanctions_list.json"
)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}

    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError:
        return {}


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)


def normalize_text(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip().lower()


def normalize_list(values: list[Any]) -> list[str]:
    return [normalize_text(value) for value in values]


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
        "agent_name": "Agent E - Sanctions Screening",
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


def check_value_against_list(
    findings: list[dict[str, Any]],
    case_id: str,
    finding_counter: int,
    check_id: str,
    document: str,
    field: str,
    value: Any,
    sanctioned_values: list[str],
    explanation_label: str,
) -> int:
    normalized_value = normalize_text(value)

    if not normalized_value:
        return finding_counter

    if normalized_value in sanctioned_values:
        findings.append(
            build_finding(
                finding_id=f"E-{case_id}-{finding_counter:03}",
                check_id=check_id,
                severity="critical",
                status="failed",
                document=document,
                field=field,
                expected_value="not sanctioned",
                actual_value=value,
                explanation=f"{explanation_label} matched the sanctions screening list.",
                policy_reference="SANCTIONS_SCREENING",
            )
        )
        finding_counter += 1

    return finding_counter


def run(run_folder: str | Path) -> dict[str, Any]:
    print("[Agent E] Sanctions Screening Agent running...")

    run_folder = Path(run_folder)

    extracted_path = run_folder / "extracted_fields.json"
    sanctions_path = SANCTIONS_LIST_PATH

    extracted = read_json(extracted_path)
    sanctions_list = read_json(sanctions_path)

    case_id = extracted.get("case_id", "UNKNOWN")
    findings = []
    finding_counter = 1

    if not extracted:
        findings.append(
            build_finding(
                finding_id=f"E-{case_id}-INPUT-001",
                check_id="INPUT-001",
                severity="minor",
                status="warning",
                document="extracted_fields.json",
                field="file",
                expected_value="valid extracted_fields.json",
                actual_value="missing_or_invalid",
                explanation=f"extracted_fields.json is missing or invalid at: {extracted_path}",
                policy_reference="INPUT_VALIDATION",
            )
        )

    if not sanctions_list:
        findings.append(
            build_finding(
                finding_id=f"E-{case_id}-INPUT-002",
                check_id="INPUT-002",
                severity="minor",
                status="warning",
                document="sanctions_list.json",
                field="file",
                expected_value="valid sanctions_list.json",
                actual_value="missing_or_invalid",
                explanation=f"sanctions list is missing or invalid at: {sanctions_path}",
                policy_reference="INPUT_VALIDATION",
            )
        )

    if not extracted or not sanctions_list:
        result = {
            "case_id": case_id,
            "findings": findings,
        }

        output_path = run_folder / "sanctions_result.json"
        write_json(output_path, result)

        print("Agent E completed with input warning")
        print(f"sanctions_result.json created at: {output_path}")
        print(f"Findings created: {len(findings)}")

        return result

    sanctioned_parties = normalize_list(sanctions_list.get("sanctioned_parties", []))
    sanctioned_countries = normalize_list(sanctions_list.get("sanctioned_countries", []))
    sanctioned_ports = normalize_list(sanctions_list.get("sanctioned_ports", []))
    sanctioned_vessels = normalize_list(sanctions_list.get("sanctioned_vessels", []))

    lc = extracted.get("letter_of_credit", {})
    invoice = extracted.get("commercial_invoice", {})
    bol = extracted.get("bill_of_lading", {})
    coo = extracted.get("certificate_of_origin", {})

    party_checks = [
        ("SAN-001", "letter_of_credit", "applicant", lc.get("applicant"), "Applicant"),
        ("SAN-002", "letter_of_credit", "beneficiary", lc.get("beneficiary"), "Beneficiary"),
        ("SAN-003", "commercial_invoice", "buyer", invoice.get("buyer"), "Buyer"),
        ("SAN-004", "commercial_invoice", "seller", invoice.get("seller"), "Seller"),
        ("SAN-005", "bill_of_lading", "shipper", bol.get("shipper"), "Shipper"),
        ("SAN-006", "bill_of_lading", "consignee", bol.get("consignee"), "Consignee"),
        ("SAN-007", "certificate_of_origin", "exporter", coo.get("exporter"), "Exporter"),
    ]

    for check_id, document, field, value, label in party_checks:
        finding_counter = check_value_against_list(
            findings=findings,
            case_id=case_id,
            finding_counter=finding_counter,
            check_id=check_id,
            document=document,
            field=field,
            value=value,
            sanctioned_values=sanctioned_parties,
            explanation_label=label,
        )

    country_checks = [
        ("SAN-008", "certificate_of_origin", "country_of_origin", coo.get("country_of_origin"), "Country of origin"),
        ("SAN-009", "letter_of_credit", "country", lc.get("country"), "Letter of Credit country"),
    ]

    for check_id, document, field, value, label in country_checks:
        finding_counter = check_value_against_list(
            findings=findings,
            case_id=case_id,
            finding_counter=finding_counter,
            check_id=check_id,
            document=document,
            field=field,
            value=value,
            sanctioned_values=sanctioned_countries,
            explanation_label=label,
        )

    port_checks = [
        ("SAN-010", "bill_of_lading", "port_of_loading", bol.get("port_of_loading"), "Port of loading"),
        ("SAN-011", "bill_of_lading", "port_of_discharge", bol.get("port_of_discharge"), "Port of discharge"),
    ]

    for check_id, document, field, value, label in port_checks:
        finding_counter = check_value_against_list(
            findings=findings,
            case_id=case_id,
            finding_counter=finding_counter,
            check_id=check_id,
            document=document,
            field=field,
            value=value,
            sanctioned_values=sanctioned_ports,
            explanation_label=label,
        )

    vessel_checks = [
        ("SAN-012", "bill_of_lading", "vessel_name", bol.get("vessel_name"), "Vessel"),
        ("SAN-013", "bill_of_lading", "vessel", bol.get("vessel"), "Vessel"),
    ]

    for check_id, document, field, value, label in vessel_checks:
        finding_counter = check_value_against_list(
            findings=findings,
            case_id=case_id,
            finding_counter=finding_counter,
            check_id=check_id,
            document=document,
            field=field,
            value=value,
            sanctioned_values=sanctioned_vessels,
            explanation_label=label,
        )

    result = {
        "case_id": case_id,
        "findings": findings,
    }

    output_path = run_folder / "sanctions_result.json"
    write_json(output_path, result)

    print("Agent E completed")
    print(f"sanctions_result.json created at: {output_path}")
    print(f"Findings created: {len(findings)}")

    return result


if __name__ == "__main__":
    run("runs/run_001")
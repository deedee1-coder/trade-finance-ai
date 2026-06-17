import json
from pathlib import Path
from typing import Any


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


def normalize_text(value: str | None) -> str:
    if value is None:
        return ""

    return value.strip().lower()


def build_match(
    check_id: str,
    field: str,
    expected_value: Any,
    actual_value: Any,
    description: str
) -> dict:

    return {
        "check_id": check_id,
        "field": field,
        "result": "pass",
        "expected_value": expected_value,
        "actual_value": actual_value,
        "description": description
    }


def build_mismatch(
    finding_id: str,
    severity: str,
    document: str,
    field: str,
    expected_value: Any,
    actual_value: Any,
    explanation: str
) -> dict:

    return {
        "finding_id": finding_id,
        "severity": severity,
        "document": document,
        "field": field,
        "expected_value": expected_value,
        "actual_value": actual_value,
        "explanation": explanation
    }


def run(run_folder: str | Path) -> dict:

    print("[Agent D] Cross Document Matching Agent running...")

    run_folder = Path(run_folder)

    extracted_path = run_folder / "extracted_fields.json"

    extracted = read_json(extracted_path)

    matches = []
    mismatches = []
    errors = []

    case_id = extracted.get("case_id", "UNKNOWN")

    lc = extracted.get("letter_of_credit", {})
    invoice = extracted.get("commercial_invoice", {})
    bol = extracted.get("bill_of_lading", {})
    coo = extracted.get("certificate_of_origin", {})

    # ==================================================
    # MATCH-001 Amount
    # ==================================================

    lc_amount = lc.get("amount")
    invoice_amount = invoice.get("amount")

    if lc_amount is not None and invoice_amount is not None:

        if float(lc_amount) == float(invoice_amount):

            matches.append(
                build_match(
                    "MATCH-001",
                    "amount",
                    lc_amount,
                    invoice_amount,
                    "Commercial invoice amount matches the Letter of Credit amount."
                )
            )

        else:

            difference = float(invoice_amount) - float(lc_amount)

            mismatches.append(
                build_mismatch(
                    f"D-{case_id}-001",
                    "medium",
                    "commercial_invoice",
                    "amount",
                    lc_amount,
                    invoice_amount,
                    f"Commercial invoice amount exceeds the Letter of Credit amount by USD {difference:.0f}."
                )
            )

    # ==================================================
    # MATCH-002 Currency
    # ==================================================

    lc_currency = lc.get("currency")
    invoice_currency = invoice.get("currency")

    if lc_currency and invoice_currency:

        if normalize_text(lc_currency) == normalize_text(invoice_currency):

            matches.append(
                build_match(
                    "MATCH-002",
                    "currency",
                    lc_currency,
                    invoice_currency,
                    "Commercial invoice currency matches the Letter of Credit currency."
                )
            )

        else:

            mismatches.append(
                build_mismatch(
                    f"D-{case_id}-002",
                    "medium",
                    "commercial_invoice",
                    "currency",
                    lc_currency,
                    invoice_currency,
                    "Commercial invoice currency does not match the Letter of Credit currency."
                )
            )

    # ==================================================
    # MATCH-003 Applicant / Buyer / Consignee
    # ==================================================

    applicant = normalize_text(lc.get("applicant"))
    buyer = normalize_text(invoice.get("buyer"))
    consignee = normalize_text(bol.get("consignee"))

    if applicant and buyer and consignee:

        if applicant == buyer == consignee:

            matches.append(
                build_match(
                    "MATCH-003",
                    "applicant",
                    lc.get("applicant"),
                    invoice.get("buyer"),
                    "Applicant, Buyer and Consignee match."
                )
            )

        else:

            mismatches.append(
                build_mismatch(
                    f"D-{case_id}-003",
                    "medium",
                    "multiple_documents",
                    "applicant",
                    lc.get("applicant"),
                    invoice.get("buyer"),
                    "Applicant, Buyer and Consignee values do not match."
                )
            )

    # ==================================================
    # MATCH-004 Beneficiary Group
    # ==================================================

    beneficiary = normalize_text(lc.get("beneficiary"))
    seller = normalize_text(invoice.get("seller"))
    shipper = normalize_text(bol.get("shipper"))
    exporter = normalize_text(coo.get("exporter"))

    if beneficiary and seller and shipper and exporter:

        if beneficiary == seller == shipper == exporter:

            matches.append(
                build_match(
                    "MATCH-004",
                    "beneficiary",
                    lc.get("beneficiary"),
                    invoice.get("seller"),
                    "Beneficiary, Seller, Shipper and Exporter match."
                )
            )

        else:

            mismatches.append(
                build_mismatch(
                    f"D-{case_id}-004",
                    "medium",
                    "multiple_documents",
                    "beneficiary",
                    lc.get("beneficiary"),
                    invoice.get("seller"),
                    "Beneficiary, Seller, Shipper and Exporter values do not match."
                )
            )

    status = "success"

    if mismatches:
        status = "manual_review_required"

    result = {
        "case_id": case_id,
        "agent_name": "Agent D - Cross Document Matching",
        "status": status,
        "matches": matches,
        "mismatches": mismatches,
        "errors": errors
    }

    output_path = run_folder / "match_result.json"

    write_json(output_path, result)

    print("Agent D completed")
    print(f"match_result.json created at: {output_path}")

    return result


if __name__ == "__main__":
    run("runs/run_001")
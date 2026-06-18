import json
from pathlib import Path
from typing import Any

import yaml
from rapidfuzz import fuzz

# Names this similar (0-100) are treated as the same party (handles spelling/format variations).
NAME_MATCH_THRESHOLD = 85


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


def amount_tolerance_pct() -> float:
    # UCP 600 allows a small tolerance on the L/C amount; read it from the policy pack.
    try:
        policy = yaml.safe_load((Path("policies") / "policy_pack.yaml").read_text(encoding="utf-8")) or {}
        return float(policy.get("examination", {}).get("amount_tolerance_pct", 0.0))
    except Exception:
        return 0.0


def names_match(a: str, b: str) -> bool:
    # Fuzzy comparison so variations still match — token_set_ratio also matches a name
    # whether or not a trailing address is included (e.g. "ABC Ltd" vs "ABC Ltd, Milan").
    if not a or not b:
        return False
    return fuzz.token_set_ratio(a, b) >= NAME_MATCH_THRESHOLD


def is_to_order(consignee: str) -> bool:
    # A negotiable ("to order") bill of lading is standard practice and is NOT a party mismatch.
    return "to order" in consignee


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
        "agent_name": "Agent D - Cross Document Matching",
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


def run(run_folder: str | Path) -> dict[str, Any]:
    print("[Agent D] Cross Document Matching Agent running...")

    run_folder = Path(run_folder)
    extracted_path = run_folder / "extracted_fields.json"

    extracted = read_json(extracted_path)
    case_id = extracted.get("case_id", "UNKNOWN")

    findings = []

    if not extracted:
        findings.append(
            build_finding(
                finding_id=f"D-{case_id}-INPUT-001",
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

        result = {
            "case_id": case_id,
            "findings": findings,
        }

        output_path = run_folder / "match_result.json"
        write_json(output_path, result)

        print("Agent D completed with input error")
        print(f"match_result.json created at: {output_path}")

        return result

    lc = extracted.get("letter_of_credit", {})
    invoice = extracted.get("commercial_invoice", {})
    bol = extracted.get("bill_of_lading", {})
    coo = extracted.get("certificate_of_origin", {})

    # ==================================================
    # MATCH-001 Amount
    # ==================================================

    lc_amount = lc.get("amount")
    invoice_amount = invoice.get("amount")

    if lc_amount is None or invoice_amount is None:
        findings.append(
            build_finding(
                finding_id=f"D-{case_id}-001",
                check_id="MATCH-001",
                severity="minor",
                status="warning",
                document="commercial_invoice",
                field="amount",
                expected_value=lc_amount if lc_amount is not None else "amount from Letter of Credit",
                actual_value=invoice_amount if invoice_amount is not None else "missing invoice amount",
                explanation="Amount matching could not be completed because one of the required amount values is missing.",
                policy_reference="CROSS_DOCUMENT_AMOUNT_MATCH",
            )
        )
    else:
        try:
            lc_amount_float = float(lc_amount)
            invoice_amount_float = float(invoice_amount)

            difference = invoice_amount_float - lc_amount_float
            tolerance_pct = amount_tolerance_pct()
            percent_diff = abs(difference) / lc_amount_float * 100 if lc_amount_float else 100.0

            if percent_diff > tolerance_pct:
                findings.append(
                    build_finding(
                        finding_id=f"D-{case_id}-002",
                        check_id="MATCH-001",
                        severity="major",
                        status="failed",
                        document="commercial_invoice",
                        field="amount",
                        expected_value=lc_amount,
                        actual_value=invoice_amount,
                        explanation=(
                            "Commercial invoice amount does not match the Letter of Credit amount. "
                            f"Difference: USD {difference:.0f} ({percent_diff:.2f}%), "
                            f"exceeding the allowed {tolerance_pct:.1f}% tolerance."
                        ),
                        policy_reference="CROSS_DOCUMENT_AMOUNT_MATCH",
                    )
                )
        except (TypeError, ValueError):
            findings.append(
                build_finding(
                    finding_id=f"D-{case_id}-003",
                    check_id="MATCH-001",
                    severity="minor",
                    status="warning",
                    document="commercial_invoice",
                    field="amount",
                    expected_value="numeric amount values",
                    actual_value={
                        "letter_of_credit_amount": lc_amount,
                        "commercial_invoice_amount": invoice_amount,
                    },
                    explanation="Amount matching could not be completed because one or more amount values are not numeric.",
                    policy_reference="CROSS_DOCUMENT_AMOUNT_MATCH",
                )
            )

    # ==================================================
    # MATCH-002 Currency
    # ==================================================

    lc_currency = lc.get("currency")
    invoice_currency = invoice.get("currency")

    if not lc_currency or not invoice_currency:
        findings.append(
            build_finding(
                finding_id=f"D-{case_id}-004",
                check_id="MATCH-002",
                severity="minor",
                status="warning",
                document="commercial_invoice",
                field="currency",
                expected_value=lc_currency if lc_currency else "currency from Letter of Credit",
                actual_value=invoice_currency if invoice_currency else "missing invoice currency",
                explanation="Currency matching could not be completed because one of the required currency values is missing.",
                policy_reference="CROSS_DOCUMENT_CURRENCY_MATCH",
            )
        )
    elif normalize_text(lc_currency) != normalize_text(invoice_currency):
        findings.append(
            build_finding(
                finding_id=f"D-{case_id}-005",
                check_id="MATCH-002",
                severity="major",
                status="failed",
                document="commercial_invoice",
                field="currency",
                expected_value=lc_currency,
                actual_value=invoice_currency,
                explanation="Commercial invoice currency does not match the Letter of Credit currency.",
                policy_reference="CROSS_DOCUMENT_CURRENCY_MATCH",
            )
        )

    # ==================================================
    # MATCH-003 Applicant / Buyer / Consignee
    # ==================================================

    lc_applicant = lc.get("applicant")
    invoice_buyer = invoice.get("buyer")
    bol_consignee = bol.get("consignee")

    applicant = normalize_text(lc_applicant)
    buyer = normalize_text(invoice_buyer)
    consignee = normalize_text(bol_consignee)

    if not applicant or not buyer or not consignee:
        findings.append(
            build_finding(
                finding_id=f"D-{case_id}-006",
                check_id="MATCH-003",
                severity="minor",
                status="warning",
                document="multiple_documents",
                field="applicant_buyer_consignee",
                expected_value={
                    "letter_of_credit.applicant": lc_applicant,
                    "commercial_invoice.buyer": invoice_buyer,
                    "bill_of_lading.consignee": bol_consignee,
                },
                actual_value="one_or_more_values_missing",
                explanation="Applicant, buyer and consignee matching could not be completed because one or more values are missing.",
                policy_reference="CROSS_DOCUMENT_APPLICANT_MATCH",
            )
        )
    elif not names_match(applicant, buyer) or not (is_to_order(consignee) or names_match(consignee, applicant)):
        findings.append(
            build_finding(
                finding_id=f"D-{case_id}-007",
                check_id="MATCH-003",
                severity="major",
                status="failed",
                document="multiple_documents",
                field="applicant_buyer_consignee",
                expected_value=lc_applicant,
                actual_value={
                    "commercial_invoice.buyer": invoice_buyer,
                    "bill_of_lading.consignee": bol_consignee,
                },
                explanation=(
                    "Applicant, Buyer and Consignee values do not match across documents "
                    "(a 'to order' bill of lading is treated as acceptable)."
                ),
                policy_reference="CROSS_DOCUMENT_APPLICANT_MATCH",
            )
        )

    # ==================================================
    # MATCH-004 Beneficiary / Seller / Shipper / Exporter
    # ==================================================

    lc_beneficiary = lc.get("beneficiary")
    invoice_seller = invoice.get("seller")
    bol_shipper = bol.get("shipper")
    coo_exporter = coo.get("exporter")

    beneficiary = normalize_text(lc_beneficiary)
    seller = normalize_text(invoice_seller)
    shipper = normalize_text(bol_shipper)
    exporter = normalize_text(coo_exporter)

    if not beneficiary or not seller or not shipper or not exporter:
        findings.append(
            build_finding(
                finding_id=f"D-{case_id}-008",
                check_id="MATCH-004",
                severity="minor",
                status="warning",
                document="multiple_documents",
                field="beneficiary_seller_shipper_exporter",
                expected_value={
                    "letter_of_credit.beneficiary": lc_beneficiary,
                    "commercial_invoice.seller": invoice_seller,
                    "bill_of_lading.shipper": bol_shipper,
                    "certificate_of_origin.exporter": coo_exporter,
                },
                actual_value="one_or_more_values_missing",
                explanation="Beneficiary, seller, shipper and exporter matching could not be completed because one or more values are missing.",
                policy_reference="CROSS_DOCUMENT_BENEFICIARY_MATCH",
            )
        )
    elif not (names_match(beneficiary, seller) and names_match(beneficiary, shipper) and names_match(beneficiary, exporter)):
        findings.append(
            build_finding(
                finding_id=f"D-{case_id}-009",
                check_id="MATCH-004",
                severity="major",
                status="failed",
                document="multiple_documents",
                field="beneficiary_seller_shipper_exporter",
                expected_value=lc_beneficiary,
                actual_value={
                    "commercial_invoice.seller": invoice_seller,
                    "bill_of_lading.shipper": bol_shipper,
                    "certificate_of_origin.exporter": coo_exporter,
                },
                explanation="Beneficiary, Seller, Shipper and Exporter values do not match across documents.",
                policy_reference="CROSS_DOCUMENT_BENEFICIARY_MATCH",
            )
        )

    result = {
        "case_id": case_id,
        "findings": findings,
    }

    output_path = run_folder / "match_result.json"
    write_json(output_path, result)

    print("Agent D completed")
    print(f"match_result.json created at: {output_path}")
    print(f"Findings created: {len(findings)}")

    return result


if __name__ == "__main__":
    run("runs/run_001")
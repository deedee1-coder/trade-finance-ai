"""Agent F: Document fraud and authenticity screening."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Patterns that reveal a document is synthetic, templated, or a test artefact.
# ---------------------------------------------------------------------------

_SYNTHETIC_PATTERNS = [
    (r"\bgenerated\s+sample\b",              "Generated sample marker"),
    (r"\bdemo[/\s]testing\b",               "Demo/testing marker"),
    (r"\bplaceholder\b",                     "Placeholder text"),
    (r"\bdummy\s+document\b",               "Dummy document marker"),
    (r"\btest\s+document\b",                "Test document marker"),
    (r"\bscenario\s*:",                     "Scenario annotation (test metadata)"),
    (r"\bsample\s+document\b",              "Sample document marker"),
    (r"\bfor\s+(?:demo|test|itfds)\b",      "Testing-purpose annotation"),
]

_COMPILED_SYNTHETIC = [
    (re.compile(p, re.IGNORECASE), label) for p, label in _SYNTHETIC_PATTERNS
]


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

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


def _build_finding(
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
        "agent_name": "Agent F - Fraud/Authenticity Screening",
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


# ---------------------------------------------------------------------------
# FRD-001: Synthetic / template document markers
# Real documents should not contain text like "Generated sample", "Scenario:",
# or testing-purpose annotations. Presence signals the document is not genuine.
# ---------------------------------------------------------------------------

def _check_synthetic_markers(
    findings: list[dict[str, Any]],
    case_id: str,
    counter: int,
    doc_type: str,
    filename: str,
    raw_text: str,
) -> int:
    hits = [label for pattern, label in _COMPILED_SYNTHETIC if pattern.search(raw_text)]
    if not hits:
        return counter

    # Core settlement documents (L/C, B/L) are the highest-risk forgery targets.
    severity = "major" if doc_type in {"letter_of_credit", "bill_of_lading"} else "minor"
    findings.append(
        _build_finding(
            finding_id=f"F-{case_id}-{counter:03}",
            check_id="FRD-001",
            severity=severity,
            status="failed",
            document=doc_type,
            field="raw_text",
            expected_value="no synthetic or template markers",
            actual_value=", ".join(hits),
            explanation=(
                f"{filename} contains markers suggesting it is synthetic or templated: "
                f"{', '.join(hits)}."
            ),
            policy_reference="FRAUD_AUTHENTICITY",
            evidence=[{"document": filename, "markers_found": hits}],
        )
    )
    return counter + 1


# ---------------------------------------------------------------------------
# FRD-002: Invoice internal arithmetic consistency
# Quantity × unit price should equal the stated total amount (within 1 %).
# A mismatch after extraction suggests the total was altered without adjusting
# the line-item detail — a common indicator of invoice manipulation.
# ---------------------------------------------------------------------------

def _check_invoice_arithmetic(
    findings: list[dict[str, Any]],
    case_id: str,
    counter: int,
    raw_text: str,
) -> int:
    qty_m = re.search(r"Quantity\s+([\d,]+)", raw_text, re.IGNORECASE)
    unit_m = re.search(r"Unit\s+Price\s+(?:USD|EUR|GBP|JPY|CNY)?\s*([\d,]+\.?\d*)", raw_text, re.IGNORECASE)
    total_m = re.search(r"Total\s+Amount\s+(?:USD|EUR|GBP|JPY|CNY)?\s*([\d,]+\.?\d*)", raw_text, re.IGNORECASE)

    if not (qty_m and unit_m and total_m):
        return counter

    try:
        qty = float(qty_m.group(1).replace(",", ""))
        unit_price = float(unit_m.group(1).replace(",", ""))
        total = float(total_m.group(1).replace(",", ""))
    except ValueError:
        return counter

    if qty <= 0 or unit_price <= 0:
        return counter

    expected = qty * unit_price
    discrepancy_pct = abs(expected - total) / expected * 100
    if discrepancy_pct > 1.0:
        findings.append(
            _build_finding(
                finding_id=f"F-{case_id}-{counter:03}",
                check_id="FRD-002",
                severity="major",
                status="failed",
                document="commercial_invoice",
                field="total_amount",
                expected_value=f"{expected:.2f} (qty {qty} × unit price {unit_price})",
                actual_value=f"{total:.2f}",
                explanation=(
                    f"Invoice total {total:.2f} does not match "
                    f"qty ({qty}) × unit price ({unit_price}) = {expected:.2f} "
                    f"(discrepancy {discrepancy_pct:.1f} %). Possible amount manipulation."
                ),
                policy_reference="FRAUD_AUTHENTICITY",
                evidence=[{
                    "document": "commercial_invoice",
                    "quantity": qty,
                    "unit_price": unit_price,
                    "stated_total": total,
                    "computed_total": round(expected, 2),
                    "discrepancy_pct": round(discrepancy_pct, 2),
                }],
            )
        )
        counter += 1
    return counter


# ---------------------------------------------------------------------------
# FRD-003: L/C reference number in invoice payment terms
# The invoice payment terms must cite the governing L/C number. A different
# reference number may indicate the invoice was prepared for another transaction
# and reused (document substitution).
# ---------------------------------------------------------------------------

def _check_lc_reference(
    findings: list[dict[str, Any]],
    case_id: str,
    counter: int,
    lc_number: str,
    invoice_raw: str,
) -> int:
    if not lc_number or not invoice_raw:
        return counter

    payment_m = re.search(r"Payment\s+Terms\s+.*?(LC[-\s][\w-]+)", invoice_raw, re.IGNORECASE)
    if not payment_m:
        return counter

    referenced = payment_m.group(1).strip()

    def _norm(s: str) -> str:
        return re.sub(r"[\s\-]", "", s).upper()

    if _norm(referenced) != _norm(lc_number):
        findings.append(
            _build_finding(
                finding_id=f"F-{case_id}-{counter:03}",
                check_id="FRD-003",
                severity="major",
                status="failed",
                document="commercial_invoice",
                field="payment_terms",
                expected_value=lc_number,
                actual_value=referenced,
                explanation=(
                    f"Invoice payment terms reference L/C '{referenced}' but the governing "
                    f"credit is '{lc_number}'. Possible document substitution."
                ),
                policy_reference="FRAUD_AUTHENTICITY",
                evidence=[{
                    "document": "commercial_invoice",
                    "lc_in_invoice": referenced,
                    "expected_lc": lc_number,
                }],
            )
        )
        counter += 1
    return counter


# ---------------------------------------------------------------------------
# FRD-004: Document date plausibility
# Checks three date-sequence rules that compliance agents do not cover:
#   (a) B/L date must not exceed L/C expiry (extreme: backdated forgery risk)
#   (b) Invoice date must not exceed L/C expiry
#   (c) Certificate of Origin issued >5 days after the B/L is unusual
# Agents C/D check UCP deadline compliance; Agent F checks logical plausibility
# as a fraud signal (e.g. someone altered a date to fall within a window).
# ---------------------------------------------------------------------------

def _parse_date(text: str) -> datetime | None:
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text.strip(), fmt)
        except ValueError:
            continue
    return None


def _first_date_in_text(raw: str) -> datetime | None:
    for m in re.finditer(r"\b(\d{4}-\d{2}-\d{2})\b", raw):
        parsed = _parse_date(m.group(1))
        if parsed:
            return parsed
    return None


def _check_date_plausibility(
    findings: list[dict[str, Any]],
    case_id: str,
    counter: int,
    documents: list[dict[str, Any]],
    lc_terms: dict[str, Any],
) -> int:
    def _lc_date(key: str) -> datetime | None:
        raw = lc_terms.get(key, "") or ""
        m = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", raw)
        return _parse_date(m.group(1)) if m else None

    expiry_date = _lc_date("expiry_date")

    doc_dates: dict[str, datetime] = {}
    for doc in documents:
        dt = _first_date_in_text(doc.get("raw_text_snippet", "") or "")
        if dt:
            doc_dates[doc.get("doc_type", "")] = dt

    bol_date = doc_dates.get("bill_of_lading")
    inv_date = doc_dates.get("commercial_invoice")
    coo_date = doc_dates.get("certificate_of_origin")

    if bol_date and expiry_date and bol_date > expiry_date:
        findings.append(
            _build_finding(
                finding_id=f"F-{case_id}-{counter:03}",
                check_id="FRD-004",
                severity="major",
                status="failed",
                document="bill_of_lading",
                field="date_of_issue",
                expected_value=f"on or before L/C expiry {expiry_date.date()}",
                actual_value=str(bol_date.date()),
                explanation=(
                    f"B/L issue date ({bol_date.date()}) is after the L/C expiry "
                    f"({expiry_date.date()}). May indicate a backdated or forged document."
                ),
                policy_reference="FRAUD_AUTHENTICITY",
                evidence=[{"bol_date": str(bol_date.date()), "lc_expiry": str(expiry_date.date())}],
            )
        )
        counter += 1

    if inv_date and expiry_date and inv_date > expiry_date:
        findings.append(
            _build_finding(
                finding_id=f"F-{case_id}-{counter:03}",
                check_id="FRD-004",
                severity="major",
                status="failed",
                document="commercial_invoice",
                field="invoice_date",
                expected_value=f"on or before L/C expiry {expiry_date.date()}",
                actual_value=str(inv_date.date()),
                explanation=(
                    f"Invoice date ({inv_date.date()}) is after the L/C expiry "
                    f"({expiry_date.date()}). Presentation after expiry is a critical risk."
                ),
                policy_reference="FRAUD_AUTHENTICITY",
                evidence=[{"invoice_date": str(inv_date.date()), "lc_expiry": str(expiry_date.date())}],
            )
        )
        counter += 1

    if coo_date and bol_date:
        delta = (coo_date - bol_date).days
        if delta > 5:
            findings.append(
                _build_finding(
                    finding_id=f"F-{case_id}-{counter:03}",
                    check_id="FRD-004",
                    severity="minor",
                    status="warning",
                    document="certificate_of_origin",
                    field="date_of_issue",
                    expected_value=f"issued on or near B/L date {bol_date.date()}",
                    actual_value=str(coo_date.date()),
                    explanation=(
                        f"Certificate of Origin issued {delta} days after the B/L "
                        f"({bol_date.date()}). Certificates typically pre-date or match the B/L."
                    ),
                    policy_reference="FRAUD_AUTHENTICITY",
                    evidence=[{
                        "coo_date": str(coo_date.date()),
                        "bol_date": str(bol_date.date()),
                        "delta_days": delta,
                    }],
                )
            )
            counter += 1

    return counter


# ---------------------------------------------------------------------------
# Risk scoring
# ---------------------------------------------------------------------------

def _risk_score(findings: list[dict[str, Any]]) -> tuple[int, str]:
    score = 0
    for f in findings:
        sev = f.get("severity", "minor")
        if sev == "critical":
            score += 40
        elif sev == "major":
            score += 20
        elif sev == "minor":
            score += 5
    score = min(score, 100)

    if score == 0:
        level = "low"
    elif score <= 15:
        level = "medium"
    elif score <= 40:
        level = "high"
    else:
        level = "critical"

    return score, level


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run(run_folder: str | Path) -> dict[str, Any]:
    print("[Agent F] Fraud/Authenticity Screening Agent running...")

    run_folder = Path(run_folder)
    extracted_docs = _read_json(run_folder / "extracted_docs.json")
    extracted_fields = _read_json(run_folder / "extracted_fields.json")
    context = _read_json(run_folder / "context.json") or _read_json(run_folder / "context_packet.json")

    case_id = (
        extracted_fields.get("case_id")
        or context.get("manifest", {}).get("case_id")
        or run_folder.name
    )
    documents: list[dict[str, Any]] = extracted_docs.get("documents", [])
    lc_terms: dict[str, Any] = context.get("lc_terms", {})

    findings: list[dict[str, Any]] = []
    counter = 1

    if not documents:
        findings.append(
            _build_finding(
                finding_id=f"F-{case_id}-INPUT-001",
                check_id="INPUT-001",
                severity="minor",
                status="warning",
                document="extracted_docs.json",
                field="file",
                expected_value="valid extracted_docs.json",
                actual_value="missing_or_invalid",
                explanation=f"extracted_docs.json is missing or has no documents at: {run_folder / 'extracted_docs.json'}",
                policy_reference="INPUT_VALIDATION",
            )
        )

    # FRD-001 — synthetic/template markers (per document)
    for doc in documents:
        doc_type = doc.get("doc_type", "unknown")
        filename = doc.get("filename", doc_type)
        counter = _check_synthetic_markers(
            findings, case_id, counter, doc_type, filename,
            doc.get("raw_text_snippet", "") or "",
        )

    # FRD-002 — invoice arithmetic
    invoice_doc = next((d for d in documents if d.get("doc_type") == "commercial_invoice"), None)
    if invoice_doc:
        counter = _check_invoice_arithmetic(
            findings, case_id, counter,
            invoice_doc.get("raw_text_snippet", "") or "",
        )

    # FRD-003 — L/C reference in invoice
    lc_number = lc_terms.get("lc_number") or extracted_fields.get("letter_of_credit", {}).get("lc_number")
    if invoice_doc and lc_number:
        counter = _check_lc_reference(
            findings, case_id, counter, lc_number,
            invoice_doc.get("raw_text_snippet", "") or "",
        )

    # FRD-004 — document date plausibility
    if documents and lc_terms:
        counter = _check_date_plausibility(findings, case_id, counter, documents, lc_terms)

    risk_score, risk_level = _risk_score(findings)

    result: dict[str, Any] = {
        "case_id": case_id,
        "overall_risk_score": risk_score,
        "overall_risk_level": risk_level,
        "findings": findings,
    }

    output_path = run_folder / "fraud_screen.json"
    _write_json(output_path, result)

    print("Agent F completed")
    print(f"fraud_screen.json created at: {output_path}")
    print(f"Fraud risk: {risk_level} (score {risk_score})")
    print(f"Findings created: {len(findings)}")

    return result


if __name__ == "__main__":
    run("runs/run_001")

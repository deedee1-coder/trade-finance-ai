def run_matching_agent(extracted_docs: dict) -> dict:
    print("[Agent D] Cross-Document Matching Agent running...")

    fields = extracted_docs["extracted_fields"]
    findings = []

    if fields["invoice_amount"] != fields["lc_amount"]:
        findings.append({
            "finding_id": "FINDING_MATCH_001",
            "agent_name": "cross_document_matching_agent",
            "finding_type": "invoice_amount_mismatch",
            "severity": "HIGH",
            "status": "OPEN",
            "message": "Invoice amount does not match LC amount.",
            "affected_fields": ["invoice_amount", "lc_amount"],
            "recommendation": "Send case to manual review."
        })

    return {
        "case_id": extracted_docs["case_id"],
        "findings": findings
    }
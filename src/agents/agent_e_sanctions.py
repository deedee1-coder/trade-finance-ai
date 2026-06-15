def run_sanctions_agent(extracted_docs: dict) -> dict:
    print("[Agent E] Sanctions Screening Agent running...")

    fields = extracted_docs["extracted_fields"]
    findings = []

    sanctioned_names = [
        "Blacklisted Shipping Ltd",
        "Sanctioned Trading Co"
    ]

    parties_to_check = [
        fields["applicant_name"],
        fields["beneficiary_name"],
        fields["vessel_name"]
    ]

    for party in parties_to_check:
        if party in sanctioned_names:
            findings.append({
                "finding_id": "FINDING_SANCTIONS_001",
                "agent_name": "sanctions_screening_agent",
                "finding_type": "sanctions_hit",
                "severity": "CRITICAL",
                "status": "OPEN",
                "message": f"Sanctions hit detected for {party}.",
                "affected_fields": ["applicant_name", "beneficiary_name", "vessel_name"],
                "recommendation": "Reject case and escalate to compliance."
            })

    return {
        "case_id": extracted_docs["case_id"],
        "findings": findings
    }
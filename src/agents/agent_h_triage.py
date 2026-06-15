def run_final_triage_agent(
    context: dict,
    extracted_docs: dict,
    all_findings: list
) -> dict:
    print("[Agent H] Final Triage Agent running...")

    if not all_findings:
        return {
            "case_id": context["case_id"],
            "final_decision": "APPROVE",
            "risk_level": "LOW",
            "summary": "No issues were found in the document bundle.",
            "decision_reasons": [
                "No compliance findings detected.",
                "No sanctions findings detected.",
                "No cross-document mismatches detected."
            ],
            "requires_manual_review": False,
            "linked_findings": [],
            "recommended_action": "Approve the case."
        }

    severities = [finding["severity"] for finding in all_findings]

    if "CRITICAL" in severities:
        final_decision = "REJECT"
        risk_level = "CRITICAL"
        requires_manual_review = True
        recommended_action = "Reject and escalate to compliance."
    elif "HIGH" in severities:
        final_decision = "MANUAL_REVIEW"
        risk_level = "HIGH"
        requires_manual_review = True
        recommended_action = "Send the case to manual review."
    else:
        final_decision = "MANUAL_REVIEW"
        risk_level = "MEDIUM"
        requires_manual_review = True
        recommended_action = "Review before approval."

    return {
        "case_id": context["case_id"],
        "final_decision": final_decision,
        "risk_level": risk_level,
        "summary": f"{len(all_findings)} finding(s) detected.",
        "decision_reasons": [
            finding["message"] for finding in all_findings
        ],
        "requires_manual_review": requires_manual_review,
        "linked_findings": [
            finding["finding_id"] for finding in all_findings
        ],
        "recommended_action": recommended_action
    }
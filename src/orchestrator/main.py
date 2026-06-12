import json
from pathlib import Path

from src.agents.agent_a_intake import run_intake_agent
from src.agents.agent_b_extraction import run_extraction_agent
from src.agents.agent_c_ucp import run_ucp_compliance_agent
from src.agents.agent_d_matching import run_matching_agent
from src.agents.agent_e_sanctions import run_sanctions_agent
from src.agents.agent_h_triage import run_final_triage_agent


def save_json(output_path: Path, data: dict) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2)


def run_case(case_id: str) -> dict:
    print(f"\nRunning pipeline for {case_id}")
    print("-" * 40)

    output_dir = Path("outputs") / case_id
    output_dir.mkdir(parents=True, exist_ok=True)

    context = run_intake_agent(case_id)
    save_json(output_dir / "context.json", context)

    extracted_docs = run_extraction_agent(context)
    save_json(output_dir / "extracted_docs.json", extracted_docs)

    ucp_result = run_ucp_compliance_agent(extracted_docs)
    save_json(output_dir / "ucp_result.json", ucp_result)

    match_result = run_matching_agent(extracted_docs)
    save_json(output_dir / "match_result.json", match_result)

    sanctions_result = run_sanctions_agent(extracted_docs)
    save_json(output_dir / "sanctions_result.json", sanctions_result)

    all_findings = []
    all_findings.extend(ucp_result["findings"])
    all_findings.extend(match_result["findings"])
    all_findings.extend(sanctions_result["findings"])

    findings_output = {
        "case_id": case_id,
        "findings": all_findings
    }
    save_json(output_dir / "findings.json", findings_output)

    decision = run_final_triage_agent(
        context=context,
        extracted_docs=extracted_docs,
        all_findings=all_findings
    )
    save_json(output_dir / "decision.json", decision)

    print("-" * 40)
    print("Pipeline completed.")
    print(f"Final decision: {decision['final_decision']}")
    print(f"Risk level: {decision['risk_level']}")

    return decision


if __name__ == "__main__":
    run_case("CASE_001")
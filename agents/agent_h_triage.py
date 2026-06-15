"""
Agent H - Exception Triage & Lead Orchestrator (Orchestrator + Judge)

Responsibilities:
- Merge, deduplicate, and prioritise findings from Agents C, D, and E
- Apply rule-based logic (policies/policy_pack.yaml) to classify discrepancies
  as major / minor and determine waivability
- Make the final trade finance decision: HONOUR / REFUSE / MANUAL_REVIEW
- Generate SWIFT MT752 (honour) or MT734 (refusal advice) message draft
- Produce human-readable discrepancy summary and full audit trail
- Ensure idempotent, deterministic decisions across re-runs

Inputs:  runs/{run_id}/context.json
         runs/{run_id}/ucp_result.json
         runs/{run_id}/match_result.json
         runs/{run_id}/sanctions_screen.json
         policies/policy_pack.yaml
Outputs: runs/{run_id}/final_decision.json
         runs/{run_id}/discrepancies.md
         runs/{run_id}/swift_draft.txt
         runs/{run_id}/audit_log.md
         runs/{run_id}/metrics.json
"""

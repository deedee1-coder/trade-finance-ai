"""
Agent C - UCP 600 Compliance

Responsibilities:
- Validate the presentation against UCP 600 (and eUCP 2.0) rules loaded from
  policies/ucp600_rules.yaml
- Key checks: expiry date, presentation period (Art. 14b), partial shipments
  (Art. 31), transhipment (Art. 20), tolerance on amount (Art. 18/37),
  document completeness (Art. 14a), originals requirement (Art. 17)
- Return PASS / FAIL / WARNING per rule with evidence reference

Inputs:  runs/{run_id}/context.json
         runs/{run_id}/extracted_docs.json
         policies/ucp600_rules.yaml
Outputs: runs/{run_id}/ucp_result.json
"""

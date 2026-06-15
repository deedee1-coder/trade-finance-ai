"""
Agent E - Sanctions Screening Engine

Responsibilities:
- Screen all named parties (applicant, beneficiary, banks, vessel owner) and
  countries against OFAC SDN, EU Consolidated, and UN Consolidated lists
  (data/sanctions_lists/)
- Apply country-level embargo checks and dual-use goods controls
- Handle multi-party transactions: correspondent banks, vessel ownership chains
- Return per-party CLEAR / HIT / REVIEW status with hit evidence
- Flag processing freeze immediately on confirmed hit

Inputs:  runs/{run_id}/context.json
         data/sanctions_lists/ofac_sdn.json
         data/sanctions_lists/eu_consolidated.json
         data/sanctions_lists/un_consolidated.json
Outputs: runs/{run_id}/sanctions_screen.json
"""

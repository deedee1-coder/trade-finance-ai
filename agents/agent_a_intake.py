"""
Agent A - Document Intake & Context (Gatekeeper)

Responsibilities:
- Load and classify all documents in the trade bundle (L/C, B/L, invoice, etc.)
- Extract key L/C fields and build the context packet
- Generate the evidence index linking each field to its source page
- Apply initial risk heuristics (new counterparties, high-risk jurisdictions,
  unusual document sets, non-compliant formats)

Inputs:  input_path/  (folder of PDFs or a single L/C PDF)
Outputs: runs/{run_id}/context.json
"""

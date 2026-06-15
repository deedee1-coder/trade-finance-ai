"""
Agent D - Cross-Document Matching

Responsibilities:
- Compare key fields across all presented documents to detect inconsistencies:
    • Beneficiary name consistency (L/C ↔ invoice ↔ B/L)
    • Goods description consistency
    • Quantity and amount consistency
    • Dates (shipment date, B/L date vs expiry, presentation date)
    • Port of loading / discharge
    • Named parties (consignee, notify party)
- Support fuzzy matching for minor name variations
- Return field-level comparison results with severity classification

Inputs:  runs/{run_id}/extracted_docs.json
         runs/{run_id}/context.json
Outputs: runs/{run_id}/match_result.json
"""

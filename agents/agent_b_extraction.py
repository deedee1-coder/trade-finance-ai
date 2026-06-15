"""
Agent B - Field Extraction

Responsibilities:
- Convert each document's raw text into structured, machine-readable fields
- Assign a confidence score (0–1) to every extracted value
- Flag low-confidence fields (e.g. degraded scans, handwritten additions) for
  manual review routing
- Output bounding-box / page-position references for traceability
- Aggregate data across all presented documents for consistent cross-doc matching

Inputs:  runs/{run_id}/context.json  +  input_path/ PDFs
Outputs: runs/{run_id}/extracted_docs.json
"""

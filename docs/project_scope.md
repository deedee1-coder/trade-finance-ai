# Project Scope

## Goal

Automate the documentary-credit examination a bank performs before honouring a
Letter of Credit: read the documents, check them against the credit terms and
UCP 600, screen for sanctions, and produce a clear, auditable, reproducible
decision with a draft SWIFT message.

## In scope

- **Input:** a Trade Bundle (Letter of Credit + commercial invoice, bill of lading,
  packing list, certificate of origin), or individual PDFs / a ZIP uploaded in the app.
- **Six-agent pipeline:** intake & context (A), field extraction (B), UCP 600
  validation (C), cross-document matching (D), sanctions screening (E), and
  triage & decision (H).
- **Outputs:** `extracted_docs.json`, `ucp_result.json`, `match_result.json`,
  `sanctions_screen.json`, `discrepancies.md`, `swift_draft.txt` (MT752/MT734),
  `audit_log.md`, and `metrics.json`.
- **Configurable policy:** thresholds, tolerances, and routing in editable YAML.
- **Streamlit app:** run a case (sample or upload) and review the result.

## Success criteria

- **Extraction accuracy** — fields captured with confidence scores.
- **Matching precision** — amounts (with tolerance), currency, and parties
  (fuzzy) reconciled across documents.
- **Deterministic outputs** — identical inputs yield identical decisions.
- **Auditability & traceability** — every decision traces to its evidence.

## Out of scope / stretch goals

- OCR for degraded scans (implemented as an optional fallback; requires Tesseract).
- Real OFAC/EU/UN consolidated lists (currently a representative sample list).
- Bounding-box coordinates per field; eUCP rules; MT700 issuance messages.
- A standalone fraud/authenticity agent and a discrepancy-waiver agent.
- Live ingestion (SWIFT FileAct / bank portal) and posting results to a tracker.

## Test scenarios

Ten sample bundles exercise the pipeline: a clean presentation, invoice amount
mismatch, sanctions hit, missing document, late shipment, late presentation,
currency mismatch, partial-shipment violation, a scan needing OCR, and an
expired Letter of Credit.

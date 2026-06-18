# Intelligent Trade Finance Document System (ITFDS)

A deterministic, multi-agent pipeline that examines trade-finance documents
(a Letter of Credit and its supporting documents) against the UCP 600 rulebook,
screens the parties for sanctions, and decides whether the bank should **honour**,
**refuse**, or send the case for **manual review** — with a full audit trail and a
draft SWIFT message.

## The pipeline

Six agents run in a fixed order, each reading and writing files in a shared run
folder (`runs/run_xxx/`):

| Agent | Role |
|-------|------|
| **A — Intake** | Validates the bundle, classifies documents, builds the case context (L/C terms, evidence index, risk flags). |
| **B — Extraction** | Reads each document into structured fields (OpenAI), with confidence scores and an OCR fallback for scanned PDFs. |
| **C — UCP 600** | Checks documents against UCP 600 (required docs, latest shipment, presentation period, expiry, partial shipment, transhipment). |
| **D — Matching** | Cross-checks documents (amounts with tolerance, currency, parties with fuzzy matching). |
| **E — Sanctions** | Screens parties, vessel, ports, and countries against the sanctions list (fuzzy matching + hit evidence). |
| **H — Decision** | Consolidates findings, applies the policy, decides honour/refuse/review, and writes all final outputs. |

## Outputs (per run, in `runs/run_xxx/`)

`context.json`, `extracted_docs.json`, `ucp_result.json`, `match_result.json`,
`sanctions_screen.json`, `final_decision.json`, `discrepancies.md`,
`swift_draft.txt`, `audit_log.md`, `metrics.json`.

## Running it

Install dependencies and launch the app:

```bash
pip install -r requirements.txt
streamlit run app/main.py
```

In the app: open **Run**, pick a sample case (or upload your own PDFs / a ZIP),
and run the pipeline; then open **Results** to see the decision, findings,
L/C terms, extracted fields, SWIFT draft, and audit log.

Set your OpenAI key first (Agent B uses it):

```bash
cp .env.example .env   # then add OPENAI_API_KEY=...
```

OCR for scanned documents is optional and also requires the Tesseract binary
(see `requirements.txt`); without it, scanned PDFs fall back to native text.

## Configuration

Rules and thresholds live in `policies/` (`policy_pack.yaml`, `ucp600_rules.yaml`)
and can be changed without touching code — amount tolerance, sanctions match
threshold, decision routing, and severities.

## Tests

```bash
pytest tests/test_e2e_pipeline.py -v
```

Runs the whole pipeline on each sample bundle and checks the decision plus
determinism (skips automatically if no OpenAI key is set).

## Design principles

- **Deterministic** — the same documents produce the same decision.
- **Auditable** — every decision traces back to its evidence.
- **Configurable** — rules and thresholds live in editable policy files.

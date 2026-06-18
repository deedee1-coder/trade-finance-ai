# System Architecture

## Overview

ITFDS is a **deterministic, file-based multi-agent pipeline**. A trade bundle goes
in; a decision (honour / refuse / manual review) plus a full set of audit artifacts
comes out. There is no message bus and no shared database — agents coordinate by
reading and writing JSON/Markdown files in a per-run folder. This makes every run
reproducible, debuggable, and auditable.

## Components

```
data/sample_documents/<case>/   trade bundles (PDFs + manifest.yaml + metadata)
        │
        ▼
orchestrator/pipeline.py         runs the agents in order, passing the run folder
        │
   ┌────┴───────────────────────────────────────────────────────────┐
   │ Agent A → Agent B → Agent C → Agent D → Agent E → Agent H         │
   └──────────────────────────────────────────────────────────────────┘
        │
        ▼
runs/run_xxx/                    all artifacts (context, results, decision, logs)
        │
        ▼
app/  (Streamlit)                reads the artifacts and presents the result
```

Shared code lives in `core/` (config, the OpenAI client, PDF/OCR utilities,
Pydantic schemas). Rules and thresholds live in `policies/` as YAML.

## The pipeline, step by step

1. **Agent A — Intake & Context.** Validates the bundle and its `manifest.yaml`,
   creates the run folder, classifies each document, and reads the Letter of Credit
   to build a context packet (`context.json`) containing the L/C terms, an evidence
   index (field → document + page), and intake risk flags.
2. **Agent B — Extraction.** Converts each PDF into structured fields with
   confidence scores (`extracted_docs.json`). Falls back to Tesseract OCR when a
   document's native text is too sparse (scanned images).
3. **Agent C — UCP 600.** Validates against UCP 600: required documents, latest
   shipment date, presentation period, expiry, partial shipment, and transhipment
   (`ucp_result.json`).
4. **Agent D — Cross-Document Matching.** Compares amounts (within a policy
   tolerance), currency, and named parties (fuzzy matching) across documents
   (`match_result.json`).
5. **Agent E — Sanctions Screening.** Screens parties, vessel, ports, and countries
   against the sanctions list using fuzzy matching, recording hit evidence
   (`sanctions_screen.json`).
6. **Agent H — Triage & Decision.** Consolidates and de-duplicates all findings,
   groups them into exception categories, applies the policy to decide
   honour/refuse/manual-review, assigns routing and a SWIFT message type, and writes
   the final artifacts: `final_decision.json`, `discrepancies.md`, `swift_draft.txt`,
   `audit_log.md`, and `metrics.json`.

## Decision logic (Agent H)

- Any **critical** finding (e.g. a sanctions hit) → **MANUAL_REVIEW / HOLD** (freeze).
- Any **major** finding → **REFUSE**.
- Only **minor** findings → **MANUAL_REVIEW**.
- No blocking findings → **HONOUR**.

## Why file-based and deterministic

Re-running identical inputs yields identical decisions, and every decision can be
traced to the artifact and document that produced it — both core success criteria.
The only non-deterministic component is Agent B's LLM extraction; the rule-based
agents (C/D/E/H) are fully deterministic given their inputs.

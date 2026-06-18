"""Results page — everything about one run, organised into tabs."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.components.decision_badge import render_decision_badge
from app.components.findings_table import render_findings_table
from app.components.metrics_row import render_metrics_row
from app.ui_helpers import extracted_field_rows, flatten_findings, load_json, load_text, run_selector

st.title("Results")

run_id = run_selector("Run to view")
if not run_id:
    st.stop()

final_decision = load_json(run_id, "final_decision.json")
context = load_json(run_id, "context.json")
extracted_docs = load_json(run_id, "extracted_docs.json")
metrics = load_json(run_id, "metrics.json")

if not final_decision:
    st.warning("This run has no final_decision.json yet.")
    st.stop()

# Headline: the decision banner and the key numbers.
render_decision_badge(final_decision)
render_metrics_row(final_decision, metrics, extracted_docs)

tabs = st.tabs(["Overview", "Findings", "L/C Terms", "Extracted Fields", "SWIFT Draft", "Audit"])

# ── Overview ──────────────────────────────────────────────────────────────────
with tabs[0]:
    summary = final_decision.get("summary")
    if summary:
        st.subheader("Summary")
        st.info(summary)

    categories = final_decision.get("exception_categories", []) or []
    st.subheader("Exception categories")
    if categories:
        st.dataframe(
            pd.DataFrame([{"Category": c["category"], "Count": c["count"]} for c in categories]),
            use_container_width=True, hide_index=True,
        )
    else:
        st.success("No exceptions — the presentation is clean.")

    risk_flags = context.get("risk_flags", []) or []
    st.subheader("Risk flags (from intake)")
    if risk_flags:
        for flag in risk_flags:
            st.write(f":material/warning: {flag}")
    else:
        st.caption("No risk flags raised at intake.")

# ── Findings ──────────────────────────────────────────────────────────────────
with tabs[1]:
    render_findings_table(flatten_findings(final_decision), "No discrepancies found.")

# ── L/C Terms (with where each came from) ─────────────────────────────────────
with tabs[2]:
    lc_terms = context.get("lc_terms", {}) or {}
    evidence = context.get("evidence_index", {}) or {}
    if lc_terms:
        rows = []
        for key, value in lc_terms.items():
            ev = evidence.get(key, {})
            source = f"{ev.get('document', '')} p.{ev.get('page', '')}" if ev else ""
            rows.append({"Term": key, "Value": value, "Source": source})
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.caption("No Letter of Credit terms were captured for this run.")

# ── Extracted fields ──────────────────────────────────────────────────────────
with tabs[3]:
    rows = extracted_field_rows(extracted_docs)
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.caption("No extracted fields found.")

# ── SWIFT draft ───────────────────────────────────────────────────────────────
with tabs[4]:
    # Use the message type Agent H decided — don't recompute it here.
    swift_type = final_decision.get("swift_message_type", "—")
    st.caption(f"Message type: {swift_type}")
    st.warning("Draft only — a human reviewer must approve any real bank message.")
    draft = load_text(run_id, "swift_draft.txt")
    if draft:
        st.code(draft, language="text")
        st.download_button("Download draft", draft, file_name=f"{run_id}_swift_draft.txt", mime="text/plain")
    else:
        st.caption("No SWIFT draft for this run.")

# ── Audit ─────────────────────────────────────────────────────────────────────
with tabs[5]:
    pipeline_status = load_json(run_id, "pipeline_status.json")
    steps = pipeline_status.get("steps", []) or []
    if steps:
        st.subheader("Pipeline steps")
        st.dataframe(pd.DataFrame(steps), use_container_width=True, hide_index=True)
    if metrics:
        st.subheader("Metrics")
        st.json(metrics)
    audit_log = load_text(run_id, "audit_log.md")
    if audit_log:
        st.subheader("Audit log")
        st.markdown(audit_log)

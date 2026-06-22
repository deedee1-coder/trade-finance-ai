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
context        = load_json(run_id, "context.json")
extracted_docs = load_json(run_id, "extracted_docs.json")
metrics        = load_json(run_id, "metrics.json")
waiver_data    = load_json(run_id, "waiver_result.json")
fraud_data     = load_json(run_id, "fraud_screen.json")

if not final_decision:
    st.warning("This run has no final_decision.json yet.")
    st.stop()

render_decision_badge(final_decision)
render_metrics_row(final_decision, metrics, extracted_docs)

tabs = st.tabs(["Overview", "Findings", "Waiver", "Fraud", "L/C Terms", "Extracted Fields", "SWIFT Draft", "Audit"])

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

    waiver_summary = final_decision.get("waiver_summary") or waiver_data.get("summary", {})
    if waiver_summary:
        st.subheader("Waiver summary")
        w1, w2, w3 = st.columns(3)
        w1.metric("Non-waivable",          waiver_summary.get("NON_WAIVABLE", 0))
        w2.metric("Needs applicant",        waiver_summary.get("WAIVABLE_NEEDS_APPLICANT", 0))
        w3.metric("Auto-waived",            waiver_summary.get("WAIVABLE_AUTO", 0))

# ── Findings ──────────────────────────────────────────────────────────────────
with tabs[1]:
    render_findings_table(flatten_findings(final_decision), "No discrepancies found.")

# ── Waiver ────────────────────────────────────────────────────────────────────
with tabs[2]:
    if not waiver_data:
        st.caption("No waiver_result.json for this run. Re-run the pipeline to generate it.")
    else:
        waiver_summary = waiver_data.get("summary", {})
        w1, w2, w3 = st.columns(3)
        w1.metric("Non-waivable",     waiver_summary.get("NON_WAIVABLE", 0),
                  help="Fraud, sanctions, missing documents, currency mismatch — cannot be waived.")
        w2.metric("Needs applicant",  waiver_summary.get("WAIVABLE_NEEDS_APPLICANT", 0),
                  help="Major findings the applicant must confirm before settlement can proceed.")
        w3.metric("Auto-waived",      waiver_summary.get("WAIVABLE_AUTO", 0),
                  help="Minor or pre-authorized findings excluded from the blocking decision.")

        classified = waiver_data.get("classified_findings", []) or []
        if classified:
            st.subheader("Classified findings")
            _WAIVER_ORDER = {"NON_WAIVABLE": 2, "WAIVABLE_NEEDS_APPLICANT": 1, "WAIVABLE_AUTO": 0}
            ordered = sorted(classified, key=lambda r: _WAIVER_ORDER.get(r.get("waiver_status", ""), 0), reverse=True)
            df_waiver = pd.DataFrame([
                {
                    "waiver_status":    r.get("waiver_status", ""),
                    "finding_id":       r.get("finding_id", ""),
                    "source":           r.get("source", ""),
                    "check_id":         r.get("check_id", ""),
                    "severity":         r.get("severity", ""),
                    "waiver_rationale": r.get("waiver_rationale", ""),
                }
                for r in ordered
            ])

            _WAIVER_BG = {
                "NON_WAIVABLE":             "#7F1D1D",
                "WAIVABLE_NEEDS_APPLICANT": "#78350F",
                "WAIVABLE_AUTO":            "#064E3B",
            }

            def _colour_ws(val: str) -> str:
                bg = _WAIVER_BG.get(str(val), "")
                return f"background-color: {bg}; color: white;" if bg else ""

            styled_waiver = df_waiver.style.map(_colour_ws, subset=["waiver_status"])
            st.dataframe(styled_waiver, use_container_width=True, hide_index=True)

# ── Fraud ─────────────────────────────────────────────────────────────────────
with tabs[3]:
    if not fraud_data:
        st.caption("No fraud_screen.json for this run. Re-run the pipeline to generate it.")
    else:
        risk_score = fraud_data.get("overall_risk_score", 0)
        risk_level = fraud_data.get("overall_risk_level", "—")

        _RISK_COLOUR = {"low": "#34D399", "medium": "#FBBF24", "high": "#F97316", "critical": "#F87171"}
        colour = _RISK_COLOUR.get(str(risk_level).lower(), "#7D8BA1")

        f1, f2 = st.columns([1, 3])
        f1.metric("Risk level", risk_level.upper())
        with f2:
            st.caption("Fraud risk score (0 – 100)")
            st.progress(int(risk_score) / 100, text=f"{risk_score} / 100")

        fraud_findings = fraud_data.get("findings", []) or []
        st.subheader("Fraud findings")
        render_findings_table(fraud_findings, "No fraud or authenticity findings.")

# ── L/C Terms ─────────────────────────────────────────────────────────────────
with tabs[4]:
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
with tabs[5]:
    rows = extracted_field_rows(extracted_docs)
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.caption("No extracted fields found.")

# ── SWIFT draft ───────────────────────────────────────────────────────────────
with tabs[6]:
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
with tabs[7]:
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

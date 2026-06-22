"""Run History page — summary of every past run."""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

from app.ui_helpers import list_runs, load_json

st.title("Run History")

runs = list_runs()
if not runs:
    st.info("No runs yet. Go to **Run Pipeline** to create one.")
    st.stop()

# ── Load summary row for every completed run ───────────────────────────────────

rows = []
for run_id in runs:
    fd = load_json(run_id, "final_decision.json")
    if not fd:
        continue
    waiver = fd.get("waiver_summary", {}) or {}
    decided_raw = fd.get("decided_at", "")
    try:
        decided = datetime.fromisoformat(decided_raw).strftime("%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        decided = decided_raw

    rows.append({
        "run_id":    run_id,
        "case_id":   fd.get("case_id", "—"),
        "decision":  fd.get("decision", "—"),
        "decided_at": decided,
        "critical":  fd.get("critical_discrepancy_count", 0),
        "major":     fd.get("major_discrepancy_count", 0),
        "minor":     fd.get("minor_discrepancy_count", 0),
        "auto_waived": waiver.get("WAIVABLE_AUTO", "—"),
        "needs_applicant": waiver.get("WAIVABLE_NEEDS_APPLICANT", "—"),
    })

if not rows:
    st.info("No completed runs found (no final_decision.json in any run folder).")
    st.stop()

df = pd.DataFrame(rows)

# ── Summary metrics ───────────────────────────────────────────────────────────

decision_counts = df["decision"].value_counts().to_dict()
total = len(df)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total runs", total)
c2.metric("Honour", decision_counts.get("HONOUR", 0))
c3.metric("Refuse", decision_counts.get("REFUSE", 0))
c4.metric("Manual review", decision_counts.get("MANUAL_REVIEW", 0))

st.divider()

# ── Decision distribution chart ───────────────────────────────────────────────

st.subheader("Decision distribution")
chart_data = pd.DataFrame(
    {"Count": decision_counts},
).rename_axis("Decision")
st.bar_chart(chart_data)

st.divider()

# ── Full run table ─────────────────────────────────────────────────────────────

st.subheader("All runs")

_DECISION_BG = {
    "HONOUR":        "background-color: #064E3B; color: white;",
    "REFUSE":        "background-color: #7F1D1D; color: white;",
    "MANUAL_REVIEW": "background-color: #78350F; color: white;",
}


def _colour_decision(value: str) -> str:
    return _DECISION_BG.get(str(value), "")


styled = df.style.map(_colour_decision, subset=["decision"])
st.dataframe(styled, use_container_width=True, hide_index=True)

st.divider()

# ── Jump to a specific run ────────────────────────────────────────────────────

st.subheader("View a run in detail")
completed_ids = df["run_id"].tolist()
default = st.session_state.get("selected_run")
idx = completed_ids.index(default) if default in completed_ids else 0
chosen = st.selectbox("Select run", completed_ids, index=idx)
if st.button("Open in Results", icon=":material/fact_check:"):
    st.session_state["selected_run"] = chosen
    st.switch_page("views/results.py")

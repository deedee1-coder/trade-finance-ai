"""The row of metric tiles shown under the decision banner."""

from __future__ import annotations

import streamlit as st


def render_metrics_row(final_decision: dict, metrics: dict, extracted_docs: dict) -> None:
    documents = len(extracted_docs.get("documents", []) or [])
    extraction = metrics.get("extraction", {}) or {}
    throughput = metrics.get("throughput", {}) or {}

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Documents", documents)
    col2.metric("Findings", final_decision.get("total_discrepancy_count", 0))
    col3.metric("Critical", final_decision.get("critical_discrepancy_count", 0))

    confidence = extraction.get("mean_confidence")
    col4.metric("Avg confidence", f"{confidence:.0%}" if isinstance(confidence, (int, float)) else "—")

    seconds = throughput.get("elapsed_seconds")
    col5.metric("Run time", f"{seconds:.1f}s" if isinstance(seconds, (int, float)) else "—")

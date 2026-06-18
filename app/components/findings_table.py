"""The findings table, with the severity column colour-coded."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from app.ui_helpers import SEVERITY_RANK

_SEVERITY_BG = {
    "critical": "#7F1D1D",
    "major": "#7C2D12",
    "minor": "#374151",
}


def _colour_severity(value: Any) -> str:
    return f"background-color: {_SEVERITY_BG.get(str(value).lower(), '')}; color: white;"


def render_findings_table(findings: list[dict[str, Any]], empty_message: str = "No findings.") -> None:
    if not findings:
        st.success(empty_message)
        return

    # Most severe first.
    ordered = sorted(findings, key=lambda f: SEVERITY_RANK.get(str(f.get("severity")).lower(), 0), reverse=True)
    rows = [
        {
            "severity": f.get("severity", ""),
            "category": f.get("source", ""),
            "check": f.get("check_id", ""),
            "document": f.get("document", ""),
            "field": f.get("field", ""),
            "explanation": f.get("explanation", ""),
        }
        for f in ordered
    ]

    styled = pd.DataFrame(rows).style.map(_colour_severity, subset=["severity"])
    st.dataframe(styled, use_container_width=True, hide_index=True)

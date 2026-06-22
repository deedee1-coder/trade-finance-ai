"""The findings table, with the severity column colour-coded."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from app.ui_helpers import SEVERITY_RANK

_SEVERITY_BG = {
    "critical": "#7F1D1D",
    "major":    "#7C2D12",
    "minor":    "#374151",
}

_WAIVER_BG = {
    "NON_WAIVABLE":             "#7F1D1D",
    "WAIVABLE_NEEDS_APPLICANT": "#78350F",
    "WAIVABLE_AUTO":            "#064E3B",
}


def _colour_severity(value: Any) -> str:
    bg = _SEVERITY_BG.get(str(value).lower(), "")
    return f"background-color: {bg}; color: white;" if bg else ""


def _colour_waiver(value: Any) -> str:
    bg = _WAIVER_BG.get(str(value), "")
    return f"background-color: {bg}; color: white;" if bg else ""


def render_findings_table(findings: list[dict[str, Any]], empty_message: str = "No findings.") -> None:
    if not findings:
        st.success(empty_message)
        return

    ordered = sorted(findings, key=lambda f: SEVERITY_RANK.get(str(f.get("severity")).lower(), 0), reverse=True)
    has_waiver = any(f.get("waiver_status") for f in ordered)

    rows = []
    for f in ordered:
        row: dict[str, Any] = {
            "severity":    f.get("severity", ""),
            "category":    f.get("source", ""),
            "check":       f.get("check_id", ""),
            "document":    f.get("document", ""),
            "field":       f.get("field", ""),
            "explanation": f.get("explanation", ""),
        }
        if has_waiver:
            row["waiver"] = f.get("waiver_status") or ""
        rows.append(row)

    df = pd.DataFrame(rows)
    style = df.style.map(_colour_severity, subset=["severity"])
    if has_waiver:
        style = style.map(_colour_waiver, subset=["waiver"])
    st.dataframe(style, use_container_width=True, hide_index=True)

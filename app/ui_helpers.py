"""Small helper functions shared by the ITFDS Streamlit pages.

These only read the files the pipeline already produced in runs/run_xxx/ — they
never run any logic themselves. Keeping them here means the pages stay short.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import streamlit as st

from core.config import settings


SEVERITY_RANK = {"critical": 3, "major": 2, "minor": 1, "info": 0}


# ── Finding the cases and runs on disk ────────────────────────────────────────

def list_sample_cases() -> list[str]:
    if not settings.SAMPLE_DOCS_DIR.exists():
        return []
    return sorted(
        path.name
        for path in settings.SAMPLE_DOCS_DIR.iterdir()
        if path.is_dir() and (path / "manifest.yaml").exists()
    )


def list_runs() -> list[str]:
    if not settings.RUN_DIR.exists():
        return []
    return sorted(
        (p.name for p in settings.RUN_DIR.iterdir() if p.is_dir() and p.name.startswith("run_")),
        reverse=True,
    )


def run_path(run_id: str) -> Path:
    return settings.RUN_DIR / run_id


# ── Reading a run's artifacts (safely) ────────────────────────────────────────

def load_json(run_id: str, filename: str) -> dict[str, Any]:
    path = run_path(run_id) / filename
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def load_text(run_id: str, filename: str) -> str:
    path = run_path(run_id) / filename
    return path.read_text(encoding="utf-8") if path.exists() else ""


# ── Shared "pick a run" dropdown (used by every page, so it lives in one place) ─

def run_selector(label: str = "Run") -> str | None:
    runs = list_runs()
    if not runs:
        st.info("No runs yet. Go to **Run Pipeline** to create one.")
        return None

    default = st.session_state.get("selected_run")
    index = runs.index(default) if default in runs else 0
    selected = st.selectbox(label, runs, index=index)
    st.session_state["selected_run"] = selected
    return selected


# ── Small formatting helpers ──────────────────────────────────────────────────

def flatten_findings(final_decision: dict[str, Any]) -> list[dict[str, Any]]:
    return [f for f in final_decision.get("discrepancies", []) if isinstance(f, dict)]


def count_severities(findings: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"critical": 0, "major": 0, "minor": 0}
    for finding in findings:
        severity = str(finding.get("severity", "")).lower()
        if severity in counts:
            counts[severity] += 1
    return counts


def extracted_field_rows(extracted_docs: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for document in extracted_docs.get("documents", []) or []:
        doc_type = document.get("doc_type") or document.get("document_type") or "unknown"
        for field_name, payload in (document.get("fields", {}) or {}).items():
            if isinstance(payload, dict):
                rows.append({
                    "document": doc_type,
                    "field": field_name,
                    "value": payload.get("value"),
                    "confidence": payload.get("confidence"),
                    "page": payload.get("page"),
                })
            else:
                rows.append({"document": doc_type, "field": field_name, "value": payload,
                             "confidence": None, "page": None})
    return rows

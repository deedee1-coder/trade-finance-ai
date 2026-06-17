"""End-to-end pipeline test harness (TES-49 / I1).

Runs the WHOLE pipeline (Agent A -> B -> C -> D -> E -> H) on each sample bundle
and checks two things:
  1. each case reaches the decision its scenario calls for, and
  2. running the same case twice gives the same result (determinism).

Because the pipeline calls OpenAI in Agent B, the whole file is skipped when no
API key is set, and each test writes to a temporary folder so it never pollutes
the real runs/ directory.

Run it with:  pytest tests/test_e2e_pipeline.py -v
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.config import settings
from orchestrator.pipeline import run_pipeline

SAMPLE_DOCS = Path(__file__).parent.parent / "data" / "sample_documents"

# The decision each bundle is designed to reach.
EXPECTED_DECISION = {
    "case_001_clean": "HONOUR",
    "case_002_invoice_mismatch": "REFUSE",
    "case_003_sanctions_hit": "MANUAL_REVIEW",
    "case_004_missing_packing_list": "REFUSE",
    "case_005_late_shipment": "REFUSE",
    "case_006_late_presentation": "REFUSE",
    "case_007_currency_mismatch": "REFUSE",
    "case_008_partial_shipment_violation": "REFUSE",
    "case_009_scanned_lc_ocr_needed": "MANUAL_REVIEW",
    "case_010_expired_lc": "REFUSE",
}

# These tests need Agent B, which calls OpenAI — skip the whole file without a key.
pytestmark = pytest.mark.skipif(
    not settings.OPENAI_API_KEY,
    reason="End-to-end tests need OPENAI_API_KEY (Agent B calls OpenAI).",
)


@pytest.fixture
def isolated_runs(tmp_path, monkeypatch):
    """Send run output to a temp folder so tests don't fill up the real runs/."""
    monkeypatch.setattr(settings, "RUN_DIR", tmp_path)
    return tmp_path


def _read_decision(run_dir: Path) -> str:
    data = json.loads((run_dir / "final_decision.json").read_text(encoding="utf-8"))
    return data.get("decision")


def _fingerprint(run_dir: Path) -> tuple:
    # A stable signature of a run: the decision plus the set of findings
    # (ignoring timestamps and run ids, which always differ).
    data = json.loads((run_dir / "final_decision.json").read_text(encoding="utf-8"))
    findings = sorted(
        f"{f.get('source')}|{f.get('check_id')}|{f.get('severity')}|{f.get('field')}"
        for f in data.get("discrepancies", [])
    )
    return data.get("decision"), tuple(findings)


@pytest.mark.parametrize("case", sorted(EXPECTED_DECISION))
def test_case_reaches_expected_decision(case, isolated_runs):
    # case_008 needs a partial-shipment rule that Agent C doesn't implement yet (TES-23).
    if case == "case_008_partial_shipment_violation":
        pytest.xfail("Partial-shipment check not implemented in Agent C (TES-23).")

    run_dir = run_pipeline(SAMPLE_DOCS / case)
    assert _read_decision(run_dir) == EXPECTED_DECISION[case]


def test_same_input_is_deterministic(isolated_runs):
    """Running the same bundle twice must give the same decision and findings."""
    first = _fingerprint(run_pipeline(SAMPLE_DOCS / "case_001_clean"))
    second = _fingerprint(run_pipeline(SAMPLE_DOCS / "case_001_clean"))
    assert first == second

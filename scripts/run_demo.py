"""One-command demo runner for Agent A / pipeline smoke testing."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from orchestrator.pipeline import run_pipeline


CASES = {
    "case_001_clean": "Clean presentation - expect ready intake",
    "case_002_invoice_mismatch": "Invoice mismatch sample - intake should still run",
    "case_003_sanctions_hit": "Sanctions hit sample - intake should still run",
}


if __name__ == "__main__":
    case = sys.argv[1] if len(sys.argv) > 1 else "case_001_clean"
    if case not in CASES:
        print(f"Unknown case '{case}'. Choose from: {list(CASES.keys())}")
        sys.exit(1)

    bundle_path = PROJECT_ROOT / "data" / "sample_documents" / case
    run_dir = run_pipeline(bundle_path)
    print(f"Running demo for: {case}")
    print(f"Expected outcome: {CASES[case]}")
    print(f"Run created: {run_dir}")
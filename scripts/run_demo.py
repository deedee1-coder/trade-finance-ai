"""
run_demo.py - One-command demo runner

Runs the full 6-agent pipeline against one of the sample trade bundles
and prints a summary of the results to the console.

Usage:
    python scripts/run_demo.py                          # default: case_001_clean
    python scripts/run_demo.py case_002_invoice_mismatch
    python scripts/run_demo.py case_003_sanctions_hit

TODO: implement once orchestrator/pipeline.py is complete.
"""
import sys

CASES = {
    "case_001_clean": "Clean presentation — expect HONOUR",
    "case_002_invoice_mismatch": "Invoice amount mismatch — expect REFUSE or MANUAL_REVIEW",
    "case_003_sanctions_hit": "Sanctions hit on vessel — expect processing freeze",
}

if __name__ == "__main__":
    case = sys.argv[1] if len(sys.argv) > 1 else "case_001_clean"
    if case not in CASES:
        print(f"Unknown case '{case}'. Choose from: {list(CASES.keys())}")
        sys.exit(1)
    print(f"Running demo for: {case}")
    print(f"Expected outcome: {CASES[case]}")
    print("Pipeline not yet implemented — check back soon.")

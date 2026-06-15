"""
pipeline.py - Main Pipeline Runner

Orchestrates the full 6-agent trade finance pipeline:

  A (Intake) → B (Extraction) → C (UCP 600) + D (Matching) → E (Sanctions) → H (Triage)

Usage:
    from orchestrator.pipeline import run_pipeline
    run_id = run_pipeline(input_path="data/sample_documents/case_001_clean")

Each agent reads its inputs from the run directory and writes its output artifact
there, keeping the pipeline deterministic and re-runnable.
"""

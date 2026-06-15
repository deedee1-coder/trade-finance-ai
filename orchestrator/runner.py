"""Simple runner for the deterministic agent pipeline."""

from pathlib import Path

from agents.agent_a_intake import run as run_agent_a


def run_pipeline(bundle_path: str | Path) -> Path:
    # For now this starts the pipeline with Agent A only.
    run_dir = run_agent_a(bundle_path)
    return run_dir

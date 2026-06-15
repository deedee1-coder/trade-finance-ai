"""Main pipeline runner for the deterministic agent workflow."""

from __future__ import annotations

from pathlib import Path

from agents.agent_a_intake import run as run_agent_a


def run_pipeline(input_path: str | Path) -> Path:
    # Agent A is implemented now. Later this will continue with B, C, D, E, and H.
    run_dir = run_agent_a(input_path)
    return run_dir
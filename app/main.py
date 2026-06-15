"""CLI entry point for the trade finance AI project."""

from __future__ import annotations

import argparse

from orchestrator.runner import run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the trade finance document pipeline.")
    parser.add_argument("--bundle", required=True, help="Path to a trade document bundle folder.")
    args = parser.parse_args()

    run_dir = run_pipeline(args.bundle)
    print(f"Run created: {run_dir}")


if __name__ == "__main__":
    main()

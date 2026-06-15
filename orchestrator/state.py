"""
state.py - Run State Management

Helpers for reading and listing pipeline run artifacts.

Key functions (to implement):
    list_runs()                          -> list of run_id strings
    get_run_dir(run_id)                  -> Path to runs/{run_id}/
    get_run_artifact(run_id, name)       -> parsed JSON dict (e.g. "context.json")
    load_markdown(run_id, name)          -> raw markdown string (e.g. "audit_log.md")
    load_text(run_id, name)              -> raw text string (e.g. "swift_draft.txt")
"""

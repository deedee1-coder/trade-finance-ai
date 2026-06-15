"""
decision_badge.py - Reusable decision banner component

Renders a coloured banner for the final pipeline decision:
  HONOUR      → green
  REFUSE      → red
  MANUAL_REVIEW → yellow

Usage:
    from app.components.decision_badge import render_decision_badge
    render_decision_badge(decision="HONOUR", rationale="All documents compliant.")
"""

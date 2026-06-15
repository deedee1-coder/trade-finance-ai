"""
findings_table.py - Reusable findings/discrepancy table component

Renders a styled dataframe of discrepancies with severity badges
(major = 🔴, minor = 🟡, info = 🟢) and source labels.

Usage:
    from app.components.findings_table import render_findings_table
    render_findings_table(discrepancies=[...])
"""

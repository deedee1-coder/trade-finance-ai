"""
Page 2 - Examination Results

Features (to implement):
- Run selector dropdown (lists all completed runs)
- Final decision banner (HONOUR / REFUSE / MANUAL_REVIEW) with colour coding
- Tabs:
    Summary          — key stats, discrepancy counts by severity
    Extracted Fields — per-document field table with confidence scores
    UCP 600 Checks   — rule-by-rule pass/fail table (Art. 14, 18, 20, 31, etc.)
    Cross-Doc Match  — field comparison table across documents
    Discrepancies    — full discrepancy list with severity, evidence, waivability
"""
import streamlit as st

st.set_page_config(page_title="Results | ITFDS", page_icon="📊", layout="wide")
st.title("📊 Examination Results")
st.info("Select a completed run to view results here.")

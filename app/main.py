"""
ITFDS - Intelligent Trade Finance Document System
Streamlit entry point.

Run from the project root:
    streamlit run app/main.py

Pages (auto-discovered from app/pages/):
    1_Upload.py      — upload trade bundle and trigger the pipeline
    2_Results.py     — view extracted fields, UCP checks, discrepancies, final decision
    3_Audit.py       — audit log, run metrics, sanctions screening detail
    4_SWIFT_Draft.py — view and download the generated SWIFT MT752/MT734 draft
"""
import streamlit as st

st.set_page_config(
    page_title="ITFDS — Intelligent Trade Finance",
    page_icon="🏦",
    layout="wide",
)

st.title("🏦 Intelligent Trade Finance Document System")
st.caption("Genpact Capstone Project · Multi-agent Documentary Credit Examination")

st.markdown(
    """
    Use the **sidebar** to navigate between sections:

    | Page | Purpose |
    |------|---------|
    | 📄 Upload | Submit a trade bundle and run the 6-agent pipeline |
    | 📊 Results | View findings, discrepancies, and the final decision |
    | 🔍 Audit | Step-by-step audit trail and run metrics |
    | 📨 SWIFT Draft | Generated MT752 / MT734 message ready for review |
    """
)

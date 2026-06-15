"""Streamlit entry point for ITFDS."""

import streamlit as st

st.set_page_config(
    page_title="ITFDS - Intelligent Trade Finance",
    page_icon="bank",
    layout="wide",
)

st.title("Intelligent Trade Finance Document System")
st.caption("Multi-agent documentary credit examination")

st.markdown(
    """
    Use the sidebar to navigate between sections:

    | Page | Purpose |
    |------|---------|
    | Upload | Submit a trade bundle and run the pipeline |
    | Results | View findings, discrepancies, and the final decision |
    | Audit | Review audit trail and metrics |
    | SWIFT Draft | Review generated SWIFT draft text |
    """
)
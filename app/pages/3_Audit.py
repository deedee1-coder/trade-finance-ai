"""
Page 3 - Audit Log & Metrics

Features (to implement):
- Run selector dropdown
- Metric cards: documents processed, avg confidence, total duration, decision
- Full audit_log.md rendered as markdown (step-by-step agent trace)
- Sanctions screening detail table (party → status → hit evidence)
- metrics.json visualised as bar/pie charts (discrepancy rate, confidence dist.)
"""
import streamlit as st

st.set_page_config(page_title="Audit | ITFDS", page_icon="🔍", layout="wide")
st.title("🔍 Audit Log & Metrics")
st.info("Select a completed run to view the audit trail here.")

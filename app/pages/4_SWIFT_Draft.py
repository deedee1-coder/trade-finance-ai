"""
Page 4 - SWIFT Message Draft

Features (to implement):
- Run selector dropdown
- Message type badge: MT752 (Authorisation to Pay) or MT734 (Advice of Refusal)
- Full SWIFT draft displayed in a monospace code block
- Download button to save swift_draft.txt
- Note: drafts are for review only — human authorisation required before sending
"""
import streamlit as st

st.set_page_config(page_title="SWIFT Draft | ITFDS", page_icon="📨", layout="wide")
st.title("📨 SWIFT Message Draft")
st.info("Select a completed run to view the generated SWIFT draft here.")

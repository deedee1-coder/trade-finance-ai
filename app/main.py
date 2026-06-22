"""ITFDS entry point — uses Streamlit's native top navbar instead of the sidebar.

Run with:  streamlit run app/main.py
"""

import sys
from pathlib import Path

# Make sure the project root is importable no matter how Streamlit is launched.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

st.set_page_config(
    page_title="ITFDS",
    page_icon=":material/account_balance:",
    layout="wide",
)

# Define the pages and put the navigation across the TOP (not the sidebar).
about   = st.Page("views/about.py",   title="About",   icon=":material/info:",        default=True)
run     = st.Page("views/run.py",     title="Run",     icon=":material/play_arrow:")
results = st.Page("views/results.py", title="Results", icon=":material/fact_check:")
history = st.Page("views/history.py", title="History", icon=":material/history:")

st.navigation([about, run, results, history], position="top").run()

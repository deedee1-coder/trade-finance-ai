"""Upload page for running the pipeline from Streamlit."""

from pathlib import Path

import streamlit as st

from core.config import settings
from orchestrator.pipeline import run_pipeline

st.set_page_config(page_title="Upload | ITFDS", page_icon="upload", layout="wide")
st.title("Upload Trade Bundle")

cases = sorted(path.name for path in settings.SAMPLE_DOCS_DIR.iterdir() if path.is_dir())
selected_case = st.selectbox("Sample case", cases)

if st.button("Run Pipeline"):
    run_dir = run_pipeline(settings.SAMPLE_DOCS_DIR / selected_case)
    st.success(f"Run created: {run_dir.name}")
    st.code(str(run_dir), language="text")
    context_path = Path(run_dir) / "context_packet.json"
    if context_path.exists():
        st.json(context_path.read_text(encoding="utf-8"))
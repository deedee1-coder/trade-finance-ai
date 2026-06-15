"""
Page 1 - Upload Trade Bundle

Features (to implement):
- Mode A: Select a sample case (case_001_clean, case_002_invoice_mismatch,
          case_003_sanctions_hit) for quick demo runs
- Mode B: Upload custom PDFs (L/C, B/L, invoice, packing list, cert of origin, etc.)
- "Run Pipeline" button → calls orchestrator.pipeline.run_pipeline()
- Live progress display as each agent completes
- On success: shows run_id and links to Results page
"""
import streamlit as st

st.set_page_config(page_title="Upload | ITFDS", page_icon="📄", layout="wide")
st.title("📄 Upload Trade Bundle")
st.info("Upload functionality will be implemented here.")

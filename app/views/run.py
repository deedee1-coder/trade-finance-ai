"""Run page — run a built-in sample case OR your own uploaded documents."""

from __future__ import annotations

import io
import json
import tempfile
import zipfile
from pathlib import Path

import yaml
import streamlit as st

from app.ui_helpers import list_sample_cases, load_json
from core.config import settings
from core.pdf_utils import classify_by_filename
from orchestrator.pipeline import run_pipeline

st.title("Run Pipeline")

STEPS = [
    "agent_a_intake", "agent_b_extraction",
    "agent_c_ucp600", "agent_d_matching", "agent_e_sanctions", "agent_f_fraud",
    "agent_g_waiver", "agent_h_triage",
]


def run_and_report(bundle_path: Path) -> None:
    """Run the pipeline on a bundle folder and show step-by-step progress."""
    with st.status("Running the eight-agent pipeline…", expanded=True) as status:
        st.write("Starting Agent A → B → [C D E F] → G → H")
        try:
            run_dir = run_pipeline(bundle_path)
        except Exception as exc:  # show the error instead of a blank screen
            status.update(label="Pipeline failed", state="error")
            st.error(f"Pipeline failed: {exc}")
            return

        pipeline_status = load_json(run_dir.name, "pipeline_status.json")
        done = {s.get("agent"): s.get("status") for s in pipeline_status.get("steps", [])}
        for step in STEPS:
            result = done.get(step, "completed" if step == "agent_a_intake" else "unknown")
            icon = "✅" if result == "completed" else ("❌" if result == "failed" else "•")
            st.write(f"{icon} {step}")
        status.update(label=f"Done — created {run_dir.name}", state="complete")

    st.session_state["selected_run"] = run_dir.name
    st.success(f"Run complete: {run_dir.name}")
    st.page_link("views/results.py", label="View results", icon=":material/fact_check:")


def collect_pdfs(uploaded_files) -> dict[str, bytes]:
    """Turn the uploaded files into {filename: bytes}, unzipping any .zip."""
    pdfs: dict[str, bytes] = {}
    for upload in uploaded_files:
        data = upload.getvalue()
        if upload.name.lower().endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                for member in archive.namelist():
                    name = Path(member).name  # flatten any folders inside the zip
                    if name.lower().endswith(".pdf"):
                        pdfs[name] = archive.read(member)
        elif upload.name.lower().endswith(".pdf"):
            pdfs[Path(upload.name).name] = data
    return pdfs


def build_bundle(pdfs: dict[str, bytes]) -> Path:
    """Write the PDFs + an auto-generated manifest.yaml into a temp folder."""
    bundle_dir = Path(tempfile.mkdtemp(prefix="itfds_upload_"))
    for name, data in pdfs.items():
        (bundle_dir / name).write_bytes(data)

    manifest = {"case_id": "uploaded_bundle", "required_documents": sorted(pdfs.keys())}
    (bundle_dir / "manifest.yaml").write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    return bundle_dir


source = st.radio("Where are the documents from?", ["Sample case", "Upload your own"], horizontal=True)

# ── Option 1: a built-in sample case ──────────────────────────────────────────
if source == "Sample case":
    cases = list_sample_cases()
    if not cases:
        st.error("No sample cases found in data/sample_documents.")
        st.stop()

    selected = st.selectbox("Choose a trade bundle", cases)
    bundle = settings.SAMPLE_DOCS_DIR / selected

    left, right = st.columns(2)
    with left:
        st.subheader("Documents")
        for name in sorted(p.name for p in bundle.iterdir() if p.suffix.lower() == ".pdf"):
            st.write(f":material/description: {name}")
    with right:
        st.subheader("Case notes")
        metadata_path = bundle / "case_metadata.json"
        if metadata_path.exists():
            try:
                meta = json.loads(metadata_path.read_text(encoding="utf-8"))
                st.write(f"**Scenario:** {meta.get('scenario', meta.get('case_name', '—'))}")
                if meta.get("expected_result"):
                    st.write(f"**Expected:** {meta['expected_result']}")
            except json.JSONDecodeError:
                st.caption("case_metadata.json is not valid JSON.")
        else:
            st.caption("No case notes for this bundle.")

    st.warning("Running calls OpenAI through Agent B and may use credits.", icon=":material/bolt:")
    if st.button("Run pipeline", type="primary", icon=":material/play_arrow:"):
        run_and_report(bundle)

# ── Option 2: your own uploaded documents ─────────────────────────────────────
else:
    st.caption("Upload individual PDFs or a single .zip containing PDFs.")
    uploaded = st.file_uploader("Upload documents", type=["pdf", "zip"], accept_multiple_files=True)

    if uploaded:
        pdfs = collect_pdfs(uploaded)
        if not pdfs:
            st.error("No PDF files found in what you uploaded.")
            st.stop()

        st.subheader("Detected documents")
        unknown = 0
        for name in sorted(pdfs):
            doc_type = classify_by_filename(name)
            if doc_type == "unknown":
                unknown += 1
                st.write(f":material/help: **{name}** → unknown type")
            else:
                st.write(f":material/description: **{name}** → {doc_type}")

        if unknown:
            st.warning(
                f"{unknown} file(s) couldn't be recognised by name. For best results, name files like "
                "`letter_of_credit.pdf`, `commercial_invoice.pdf`, `bill_of_lading.pdf`, etc.",
                icon=":material/warning:",
            )

        st.warning("Running calls OpenAI through Agent B and may use credits.", icon=":material/bolt:")
        if st.button("Run pipeline", type="primary", icon=":material/play_arrow:"):
            run_and_report(build_bundle(pdfs))

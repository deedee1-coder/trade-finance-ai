"""About page — what the project is and its scope."""

import streamlit as st

st.title("Intelligent Trade Finance Document System")
st.caption("A deterministic multi-agent pipeline that examines trade-finance documents and decides whether to pay.")

st.write("")

# ── Overview ──────────────────────────────────────────────────────────────────
st.subheader("Overview")
st.write(
    "Before a bank honours a Letter of Credit, an examiner has to check a set of documents — "
    "the letter of credit, commercial invoice, bill of lading, packing list and certificate of "
    "origin — against the credit terms and the UCP 600 rulebook, and screen the parties for "
    "sanctions. It is slow, manual and error-prone. ITFDS automates that examination with a chain "
    "of specialised agents and returns a clear, reproducible decision backed by a full audit trail."
)

st.divider()

# ── Scope ─────────────────────────────────────────────────────────────────────
st.subheader("Project scope")
left, right = st.columns(2)
with left:
    st.markdown("**What it does**")
    st.markdown(
        "- Takes a trade bundle (the L/C plus its supporting documents)\n"
        "- Extracts the key fields from each document\n"
        "- Validates UCP 600 compliance and cross-checks the documents\n"
        "- Screens parties, vessel and ports for sanctions\n"
        "- Decides **honour / refuse / manual review**"
    )
with right:
    st.markdown("**What it produces**")
    st.markdown(
        "- A final decision with its reasons\n"
        "- A list of discrepancies, ranked by severity\n"
        "- A draft SWIFT message (MT752 / MT734)\n"
        "- A step-by-step audit log\n"
        "- Run metrics (speed, extraction confidence, discrepancy rates)"
    )

st.divider()

# ── How it works ──────────────────────────────────────────────────────────────
st.subheader("How it works")
st.write("Six agents run in a fixed order, each reading and writing files in a shared run folder:")
steps = [
    ("A", "Intake", "Validates the bundle and builds the case context."),
    ("B", "Extraction", "Reads each document into structured fields."),
    ("C", "UCP 600", "Checks the documents against the rulebook."),
    ("D", "Matching", "Cross-checks the documents against each other."),
    ("E", "Sanctions", "Screens the parties, vessel, and ports."),
    ("H", "Decision", "Consolidates everything and decides pay / refuse / review."),
]
cols = st.columns(len(steps))
for col, (letter, name, desc) in zip(cols, steps):
    col.markdown(f"**{letter} · {name}**")
    col.caption(desc)

st.divider()

# ── Design principles ─────────────────────────────────────────────────────────
st.subheader("Design principles")
st.markdown(
    "- **Deterministic** — the same documents always produce the same decision\n"
    "- **Auditable** — every decision can be traced back to its evidence\n"
    "- **Configurable** — rules and thresholds live in editable policy files, not in code"
)

st.divider()
st.caption("Built with Python, Streamlit, and OpenAI. Capstone project — Genpact.")
st.page_link("views/run.py", label="Run a case", icon=":material/play_arrow:")

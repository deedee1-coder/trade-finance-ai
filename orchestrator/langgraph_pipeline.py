"""LangGraph orchestration layer for the ITFDS pipeline.

Wraps the existing agent run() functions as StateGraph nodes.
No agent code is modified — this file is the only addition.

Graph topology (matches the ITFDS architecture spec):

    START
      |
    intake          Agent A  — document intake + context packet
      |
    extraction      Agent B  — field extraction + confidence scoring
      |
    compat          writes extracted_fields.json for C / D / E / F
     /|\ \
    C  D  E  F      Agents C/D/E/F run in parallel (fan-out):
    |  |  |  |        C — UCP 600 compliance
    |  |  |  |        D — cross-document matching
    |  |  |  |        E — sanctions screening
    |  |  |  |        F — fraud / authenticity screening
     \|/ /
    triage          Agent H  — exception triage + SWIFT draft
      |
    [HONOUR | REFUSE | MANUAL_REVIEW]
      |
     END

The shared state only carries run_dir (a Path string) so all agents
can continue to read and write the shared run directory exactly as
they do today.  step_results uses operator.add so parallel branches
merge cleanly without overwriting each other.
"""

from __future__ import annotations

import operator
from pathlib import Path
from typing import Annotated, Any

from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict


# ---------------------------------------------------------------------------
# Shared graph state
# ---------------------------------------------------------------------------

class PipelineState(TypedDict):
    input_path: str                                              # caller sets once
    run_dir: str                                                 # Agent A writes; all others read
    step_results: Annotated[list[dict[str, Any]], operator.add] # each node appends; parallel branches merge
    final_decision: str                                          # Agent H writes; drives conditional edge


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def _ok(agent: str) -> list[dict[str, Any]]:
    return [{"agent": agent, "status": "completed"}]


def _fail(agent: str, exc: Exception) -> list[dict[str, Any]]:
    return [{"agent": agent, "status": "failed", "error": str(exc)}]


# ---------------------------------------------------------------------------
# Node: Agent A — Document Intake & Context (Gatekeeper)
# Loads the trade bundle, classifies document types, builds the context
# packet, and creates the run directory that all downstream agents share.
# ---------------------------------------------------------------------------

def node_intake(state: PipelineState) -> dict:
    from agents.agent_a_intake import run as run_a

    run_dir = run_a(state["input_path"])
    return {
        "run_dir": str(run_dir),
        "step_results": _ok("agent_a_intake"),
    }


# ---------------------------------------------------------------------------
# Node: Agent B — Field Extraction
# Converts each document's raw text into structured, machine-readable fields
# with confidence scores and bounding-box evidence pointers.
# ---------------------------------------------------------------------------

def node_extraction(state: PipelineState) -> dict:
    from agents.agent_b_extraction import run as run_b

    run_dir = Path(state["run_dir"])
    try:
        run_b(run_dir.name, run_dir / "input_documents")
        return {"step_results": _ok("agent_b_extraction")}
    except Exception as exc:
        return {"step_results": _fail("agent_b_extraction", exc)}


# ---------------------------------------------------------------------------
# Node: compat layer
# Writes extracted_fields.json so Agents C / D / E can share one schema.
# Reuses the identical function already in orchestrator/pipeline.py — no
# logic is duplicated.
# ---------------------------------------------------------------------------

def node_compat(state: PipelineState) -> dict:
    from orchestrator.pipeline import _write_extracted_fields_compat

    _write_extracted_fields_compat(Path(state["run_dir"]))
    return {}


# ---------------------------------------------------------------------------
# Node: Agent C — UCP 600 Compliance
# Validates presentation period, expiry date, partial-shipment rules, and
# transhipment restrictions against UCP 600 / eUCP.
# ---------------------------------------------------------------------------

def node_ucp600(state: PipelineState) -> dict:
    from agents.agent_c_ucp600 import run as run_c

    try:
        run_c(Path(state["run_dir"]))
        return {"step_results": _ok("agent_c_ucp600")}
    except Exception as exc:
        return {"step_results": _fail("agent_c_ucp600", exc)}


# ---------------------------------------------------------------------------
# Node: Agent D — Cross-Document Matching
# Checks descriptions, quantities, amounts, dates, and named parties for
# consistency across all presented documents.
# ---------------------------------------------------------------------------

def node_matching(state: PipelineState) -> dict:
    from agents.agent_d_matching import run as run_d

    try:
        run_d(Path(state["run_dir"]))
        return {"step_results": _ok("agent_d_matching")}
    except Exception as exc:
        return {"step_results": _fail("agent_d_matching", exc)}


# ---------------------------------------------------------------------------
# Node: Agent E — Sanctions Screening
# Screens all named parties, vessels, and jurisdictions against OFAC, EU,
# and UN consolidated lists; applies country-risk tiering.
# ---------------------------------------------------------------------------

def node_sanctions(state: PipelineState) -> dict:
    from agents.agent_e_sanctions import run as run_e

    try:
        run_e(Path(state["run_dir"]))
        return {"step_results": _ok("agent_e_sanctions")}
    except Exception as exc:
        return {"step_results": _fail("agent_e_sanctions", exc)}


# ---------------------------------------------------------------------------
# Node: Agent F — Fraud / Authenticity Screening
# Checks for synthetic document markers, invoice arithmetic consistency,
# L/C reference integrity in the invoice, and document date plausibility.
# Runs in parallel with C / D / E — reads extracted_docs.json and context.json.
# ---------------------------------------------------------------------------

def node_fraud(state: PipelineState) -> dict:
    from agents.agent_f_fraud import run as run_f

    try:
        run_f(Path(state["run_dir"]))
        return {"step_results": _ok("agent_f_fraud")}
    except Exception as exc:
        return {"step_results": _fail("agent_f_fraud", exc)}


# ---------------------------------------------------------------------------
# Node: Agent H — Exception Triage & Lead Orchestrator
# Merges and deduplicates findings from C / D / E, applies rule-based logic,
# assigns a final decision, and generates discrepancies.md + swift_draft.txt.
# ---------------------------------------------------------------------------

def node_triage(state: PipelineState) -> dict:
    from agents.agent_h_triage import run as run_h

    try:
        result = run_h(Path(state["run_dir"]))
        decision = result.get("decision", "MANUAL_REVIEW")
        return {
            "final_decision": decision,
            "step_results": _ok("agent_h_triage"),
        }
    except Exception as exc:
        return {
            "final_decision": "MANUAL_REVIEW",
            "step_results": _fail("agent_h_triage", exc),
        }


# ---------------------------------------------------------------------------
# Conditional edge — routes after Agent H based on the settlement decision
# ---------------------------------------------------------------------------

def _route_decision(state: PipelineState) -> str:
    return state.get("final_decision") or "MANUAL_REVIEW"


# ---------------------------------------------------------------------------
# Graph assembly
# ---------------------------------------------------------------------------

def build_graph():
    """Compile and return the LangGraph application."""
    graph = StateGraph(PipelineState)

    # Register nodes
    graph.add_node("intake",     node_intake)
    graph.add_node("extraction", node_extraction)
    graph.add_node("compat",     node_compat)
    graph.add_node("ucp600",     node_ucp600)
    graph.add_node("matching",   node_matching)
    graph.add_node("sanctions",  node_sanctions)
    graph.add_node("fraud",      node_fraud)
    graph.add_node("triage",     node_triage)

    # Sequential spine: intake → extraction → compat
    graph.set_entry_point("intake")
    graph.add_edge("intake",     "extraction")
    graph.add_edge("extraction", "compat")

    # Parallel fan-out: compat triggers C, D, E, F simultaneously
    graph.add_edge("compat", "ucp600")
    graph.add_edge("compat", "matching")
    graph.add_edge("compat", "sanctions")
    graph.add_edge("compat", "fraud")

    # Fan-in: triage waits for all four to complete before running
    graph.add_edge("ucp600",    "triage")
    graph.add_edge("matching",  "triage")
    graph.add_edge("sanctions", "triage")
    graph.add_edge("fraud",     "triage")

    # Conditional exit: HONOUR → settle, REFUSE → refusal desk, MANUAL_REVIEW → hold
    graph.add_conditional_edges(
        "triage",
        _route_decision,
        {
            "HONOUR":        END,
            "REFUSE":        END,
            "MANUAL_REVIEW": END,
        },
    )

    return graph.compile()


# ---------------------------------------------------------------------------
# Public entry point
# Mirrors the signature of run_pipeline() in orchestrator/pipeline.py so
# either orchestrator can be swapped in without touching callers.
# ---------------------------------------------------------------------------

def run_pipeline(input_path: str | Path) -> dict[str, Any]:
    """Run the full ITFDS pipeline via LangGraph and return the final state."""
    app = build_graph()
    initial_state: PipelineState = {
        "input_path":     str(input_path),
        "run_dir":        "",
        "step_results":   [],
        "final_decision": "",
    }
    return app.invoke(initial_state)

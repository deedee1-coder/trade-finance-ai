"""The big decision banner shown at the top of the Results page."""

from __future__ import annotations

import html

import streamlit as st


# Each decision gets a colour: green = pay, red = refuse, amber = needs a human.
_STYLES = {
    "HONOUR": ("#0E2A1C", "#34D399", "Pay"),
    "REFUSE": ("#2E1416", "#F87171", "Do not pay"),
    "MANUAL_REVIEW": ("#2E2410", "#FBBF24", "Needs review"),
}


def render_decision_badge(final_decision: dict) -> None:
    decision = final_decision.get("decision", "UNKNOWN")
    status = final_decision.get("processing_status", "")
    rationale = final_decision.get("decision_rationale", "")
    routing = final_decision.get("routing", {}) or {}

    background, border, plain = _STYLES.get(decision, ("#1A1F2B", "#7D8BA1", ""))

    routing_html = ""
    if routing:
        routing_html = (
            f"<div style='margin-top:0.6rem;font-size:0.9rem;'>"
            f"<b>Next:</b> {html.escape(routing.get('owner', ''))} &nbsp;·&nbsp; "
            f"{html.escape(routing.get('action', ''))}</div>"
        )

    st.markdown(
        f"""
        <div style="border:1px solid {border};background:{background};
                    padding:1.1rem 1.3rem;border-radius:12px;margin-bottom:1rem;">
            <div style="font-size:0.8rem;letter-spacing:0.05em;opacity:0.7;">FINAL DECISION</div>
            <div style="font-size:2rem;font-weight:700;color:{border};">
                {html.escape(decision)} <span style="font-size:1rem;opacity:0.7;">{html.escape(plain)}</span>
            </div>
            <div style="font-size:0.9rem;opacity:0.85;">Status: {html.escape(str(status))}</div>
            <div style="margin-top:0.5rem;">{html.escape(str(rationale))}</div>
            {routing_html}
        </div>
        """,
        unsafe_allow_html=True,
    )

"""
Tests for Agent E - Sanctions Screening

Scenarios to cover:
  - Known sanctioned entity returns HIT status
  - Clean party returns CLEAR status
  - Embargoed country triggers country_embargo hit type
  - Fuzzy match at score >= threshold returns REVIEW, below returns CLEAR
  - processing_frozen=True when overall_status is HIT
"""
import pytest

# TODO: import and test AgentESanctions once implemented

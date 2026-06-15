"""
Tests for Agent A - Document Intake & Context

Scenarios to cover:
  - All documents found and classified correctly from case_001_clean
  - context.json written with required fields (lc_number, expiry_date, etc.)
  - Risk flag raised when beneficiary country is high-risk
  - Single-document mode (L/C only) works without crashing
"""
import pytest

# TODO: import and test AgentAIntake once implemented

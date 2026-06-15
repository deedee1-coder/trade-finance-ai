"""
Tests for Agent B - Field Extraction

Scenarios to cover:
  - All key fields extracted from commercial invoice (invoice_number, amount, date, etc.)
  - Low confidence fields correctly identified and flagged
  - overall_confidence < 0.7 triggers manual review flag
  - Synthetic fallback activates when PDF text is too short
"""
import pytest

# TODO: import and test AgentBExtraction once implemented

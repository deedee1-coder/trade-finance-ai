from __future__ import annotations
from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field


# ── Agent A: Context Packet ───────────────────────────────────────────────────

class Party(BaseModel):
    name: str = ""
    country: str = ""
    address: str = ""


class PresentedDocument(BaseModel):
    doc_type: str
    filename: str
    page_count: int = 1


class ContextPacket(BaseModel):
    run_id: str
    input_path: str
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    lc_number: str = ""
    lc_amount: float = 0.0
    currency: str = "USD"
    expiry_date: str = ""
    presentation_period_days: int = 21
    applicant: Party = Field(default_factory=Party)
    beneficiary: Party = Field(default_factory=Party)
    issuing_bank: str = ""
    advising_bank: str = ""
    port_of_loading: str = ""
    port_of_discharge: str = ""
    goods_description: str = ""
    partial_shipments: Literal["allowed", "prohibited"] = "prohibited"
    transhipment: Literal["allowed", "prohibited"] = "prohibited"
    icc_rules: str = "UCP 600"
    required_documents: list[str] = Field(default_factory=list)
    presented_documents: list[PresentedDocument] = Field(default_factory=list)
    evidence_index: dict[str, Any] = Field(default_factory=dict)
    risk_flags: list[str] = Field(default_factory=list)
    vessel_name: str = ""
    vessel_flag: str = ""


# ── Agent B: Extracted Docs ───────────────────────────────────────────────────

class ExtractedField(BaseModel):
    value: Any = None
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    page: int = 1


class ExtractedDocument(BaseModel):
    doc_type: str
    filename: str
    fields: dict[str, ExtractedField] = Field(default_factory=dict)
    overall_confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    low_confidence_fields: list[str] = Field(default_factory=list)
    raw_text_snippet: str = ""
    ocr_used: bool = False  # True when OCR fallback was triggered for this document


class ExtractedDocs(BaseModel):
    run_id: str
    extraction_timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    documents: list[ExtractedDocument] = Field(default_factory=list)


# ── Agent C: UCP 600 Result ───────────────────────────────────────────────────

class UCPRuleCheck(BaseModel):
    rule_id: str
    article: str
    description: str
    status: Literal["PASS", "FAIL", "WARNING", "N/A"] = "N/A"
    finding: str = ""
    evidence: str = ""
    severity: Literal["major", "minor", "info"] = "info"


class UCPResult(BaseModel):
    run_id: str
    checked_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    icc_version: str = "UCP 600"
    checks: list[UCPRuleCheck] = Field(default_factory=list)
    total_pass: int = 0
    total_fail: int = 0
    total_warning: int = 0


# ── Agent D: Match Result ─────────────────────────────────────────────────────

class FieldComparison(BaseModel):
    field_name: str
    doc_a: str
    doc_b: str
    value_a: Any = None
    value_b: Any = None
    match: bool = True
    mismatch_detail: str = ""
    severity: Literal["major", "minor", "info"] = "info"


class MatchResult(BaseModel):
    run_id: str
    checked_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    comparisons: list[FieldComparison] = Field(default_factory=list)
    total_matches: int = 0
    total_mismatches: int = 0


# ── Agent E: Sanctions Screen ─────────────────────────────────────────────────

class SanctionsHit(BaseModel):
    list_name: str
    matched_name: str
    match_score: float = 0.0
    hit_type: Literal["exact", "fuzzy", "country_embargo", "vessel"] = "fuzzy"
    evidence: str = ""


class PartyScreening(BaseModel):
    party_name: str
    party_role: str
    country: str = ""
    status: Literal["CLEAR", "HIT", "REVIEW"] = "CLEAR"
    hits: list[SanctionsHit] = Field(default_factory=list)
    false_positive_analysis: str = ""


class SanctionsScreen(BaseModel):
    run_id: str
    screened_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    parties: list[PartyScreening] = Field(default_factory=list)
    overall_status: Literal["CLEAR", "HIT", "REVIEW"] = "CLEAR"
    processing_frozen: bool = False


# ── Agent H: Final Decision ───────────────────────────────────────────────────

class Discrepancy(BaseModel):
    id: str
    source: Literal["ucp", "matching", "sanctions", "intake"]
    severity: Literal["major", "minor", "info"]
    description: str
    evidence: str = ""
    waivable: bool = False
    recommendation: str = ""


class FinalDecision(BaseModel):
    run_id: str
    decided_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    decision: Literal["HONOUR", "REFUSE", "MANUAL_REVIEW"] = "MANUAL_REVIEW"
    decision_rationale: str = ""
    discrepancies: list[Discrepancy] = Field(default_factory=list)
    major_discrepancy_count: int = 0
    minor_discrepancy_count: int = 0
    swift_message_type: Literal["MT752", "MT734", "MT700"] = "MT752"


# ── Metrics ───────────────────────────────────────────────────────────────────

class Metrics(BaseModel):
    run_id: str
    total_duration_seconds: float = 0.0
    documents_processed: int = 0
    fields_extracted: int = 0
    avg_confidence: float = 0.0
    ucp_checks_run: int = 0
    discrepancy_rate: float = 0.0
    sanctions_parties_screened: int = 0
    decision: str = ""

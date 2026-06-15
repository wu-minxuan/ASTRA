"""Pydantic contracts for Phase 1 theme research."""

from typing import Any, ClassVar, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

CONTRACT_VERSION = "phase1.v1"
DATE_PATTERN = r"^\d{4}-\d{2}-\d{2}$"
SYMBOL_PATTERN = r"^\d{6}\.(SZ|SH)$"

Market = Literal["cn_a"]
Exchange = Literal["SZSE", "SSE"]
EvidenceKind = Literal[
    "concept",
    "industry",
    "business_summary",
    "financial_summary",
    "text_summary",
    "risk",
    "theme_relationship",
]
EvidenceStance = Literal["fact", "inference", "assumption"]
EvidenceSourceType = Literal[
    "fixture",
    "manual_research_note",
    "public_disclosure",
    "news",
    "research_report",
]
EvidenceConfidence = Literal["low", "medium", "high"]
PipelineStage = Literal[
    "theme_parse",
    "candidate_recall",
    "evidence_enrichment",
    "coarse_rank",
    "deep_rank",
    "report_generation",
]
ThemeResearchErrorCode = Literal[
    "invalid_request",
    "unsupported_market",
    "no_candidates",
    "internal_error",
]


class ContractModel(BaseModel):
    """Base class for strict Phase 1 contract models."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")


class ThemeResearchRequest(ContractModel):
    """User request for a Phase 1 theme research run."""

    theme: str = Field(min_length=1, max_length=40)
    market: Market = "cn_a"
    max_results: int = Field(default=5, ge=1, le=10)
    include_report: bool = True

    @field_validator("theme", mode="before")
    @classmethod
    def strip_theme(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value


class NormalizedThemeRequest(ContractModel):
    """Normalized request echoed by successful theme research responses."""

    theme: str = Field(min_length=1, max_length=40)
    normalized_query: str = Field(min_length=1, max_length=40)
    market: Market = "cn_a"
    max_results: int = Field(default=5, ge=1, le=10)
    include_report: bool = True

    @classmethod
    def from_request(cls, request: ThemeResearchRequest) -> "NormalizedThemeRequest":
        return cls(
            theme=request.theme,
            normalized_query=request.theme,
            market=request.market,
            max_results=request.max_results,
            include_report=request.include_report,
        )


class EvidenceItem(ContractModel):
    """Evidence item with source, stance, and confidence metadata."""

    id: str = Field(min_length=1)
    kind: EvidenceKind
    stance: EvidenceStance
    summary: str = Field(min_length=1)
    source_name: str = Field(min_length=1)
    source_type: EvidenceSourceType
    source_date: Optional[str] = Field(default=None, pattern=DATE_PATTERN)
    source_url: Optional[str] = None
    confidence: EvidenceConfidence


class ScoreFactor(ContractModel):
    """A named contribution to a theme research score."""

    name: str = Field(min_length=1)
    value: float
    reason: str = Field(min_length=1)


class ScoreBreakdown(ContractModel):
    """Score breakdown used for explainable ranking."""

    recall_score: float = Field(ge=0, le=100)
    coarse_score: float = Field(ge=0, le=100)
    final_score: float = Field(ge=0, le=100)
    factors: list[ScoreFactor] = Field(min_length=1)


class CandidateStock(ContractModel):
    """Candidate stock result with evidence, scores, and risk notes."""

    symbol: str = Field(pattern=SYMBOL_PATTERN)
    name: str = Field(min_length=1)
    market: Market = "cn_a"
    exchange: Exchange
    industry: str = Field(min_length=1)
    concepts: list[str] = Field(min_length=1)
    recall_sources: list[str] = Field(min_length=1)
    evidence: list[EvidenceItem] = Field(min_length=1)
    scores: ScoreBreakdown
    rank: Optional[int] = Field(default=None, ge=1)
    selection_reason: str = Field(min_length=1)
    key_risks: list[str] = Field(min_length=1)


class FocusCompany(ContractModel):
    """Company explanation block inside a research report."""

    symbol: str = Field(pattern=SYMBOL_PATTERN)
    name: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    supporting_evidence_ids: list[str] = Field(min_length=1)
    risks: list[str] = Field(min_length=1)


class ResearchReport(ContractModel):
    """Structured research report returned by Phase 1."""

    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    theme_overview: str = Field(min_length=1)
    pool_summary: str = Field(min_length=1)
    focus_companies: list[FocusCompany] = Field(min_length=1)
    risks: list[str] = Field(min_length=1)
    data_boundary: str = Field(min_length=1)
    not_investment_advice: str = Field(min_length=1)


class PipelineStageTrace(ContractModel):
    """Trace metadata for one research funnel stage."""

    stage: PipelineStage
    input_count: int = Field(ge=0)
    output_count: int = Field(ge=0)
    notes: list[str] = Field(default_factory=list)


class ThemeResearchResult(ContractModel):
    """Successful theme research result payload."""

    as_of: str = Field(pattern=DATE_PATTERN)
    pool: list[CandidateStock] = Field(default_factory=list)
    report: Optional[ResearchReport] = None
    pipeline: list[PipelineStageTrace] = Field(default_factory=list)
    data_boundary: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ThemeResearchResponse(ContractModel):
    """Successful Phase 1 theme research response."""

    contract_version: Literal["phase1.v1"] = CONTRACT_VERSION
    request: NormalizedThemeRequest
    result: ThemeResearchResult


class ThemeResearchError(ContractModel):
    """Structured error payload for theme research failures."""

    code: ThemeResearchErrorCode
    message: str = Field(min_length=1)
    details: dict[str, Any] = Field(default_factory=dict)


class ThemeResearchErrorResponse(ContractModel):
    """Error response wrapper for Phase 1 theme research."""

    contract_version: Literal["phase1.v1"] = CONTRACT_VERSION
    error: ThemeResearchError


class FixtureCompany(ContractModel):
    """Raw company record in the fixed Phase 1 fixture dataset."""

    symbol: str = Field(pattern=SYMBOL_PATTERN)
    name: str = Field(min_length=1)
    market: Market = "cn_a"
    exchange: Exchange
    industry: str = Field(min_length=1)
    concepts: list[str] = Field(min_length=1)
    recall_keywords: list[str] = Field(min_length=1)
    business_summary: str = Field(min_length=1)
    financial_summary: str = Field(min_length=1)
    text_summary: str = Field(min_length=1)
    risks: list[str] = Field(min_length=1)
    evidence: list[EvidenceItem] = Field(min_length=3)


class FixtureThemeDataset(ContractModel):
    """Fixed fixture dataset for one Phase 1 theme."""

    fixture_id: Literal["low_altitude_economy"]
    display_name: Literal["低空经济"]
    market: Market = "cn_a"
    as_of: str = Field(pattern=DATE_PATTERN)
    aliases: list[str] = Field(min_length=1)
    description: str = Field(min_length=1)
    companies: list[FixtureCompany] = Field(min_length=6)
    data_boundary: list[str] = Field(min_length=1)

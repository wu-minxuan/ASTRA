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
    "market_data_provider",
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
MarketDataProviderName = Literal["akshare", "fixture"]
ModelProviderName = Literal["fake"]
ModelPurpose = Literal["coarse_rank", "deep_rank", "report_generation"]


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


class ModelSpec(ContractModel):
    """Model configuration boundary used by ranking and report stages."""

    provider_name: ModelProviderName
    model_name: str = Field(min_length=1)
    purpose: ModelPurpose
    prompt_version: str = Field(min_length=1)
    temperature: float = Field(default=0.0, ge=0, le=2)
    max_output_tokens: int = Field(default=1024, ge=1)


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


class ProviderMetadata(ContractModel):
    """Metadata describing where provider records came from."""

    provider_name: MarketDataProviderName
    provider_interface: str = Field(min_length=1)
    retrieved_at: str = Field(min_length=1)
    is_fallback: bool = False
    failure_reason: Optional[str] = None


class StockSourceRecord(ContractModel):
    """Normalized raw stock record from a market data provider."""

    raw_symbol: str = Field(min_length=1)
    symbol: str = Field(pattern=SYMBOL_PATTERN)
    name: str = Field(min_length=1)
    market: Market = "cn_a"
    exchange: Exchange
    industry: Optional[str] = None
    listing_status: Optional[str] = None
    provider: ProviderMetadata


class ConceptBoardRecord(ContractModel):
    """Normalized concept board record from a market data provider."""

    raw_name: str = Field(min_length=1)
    concept_name: str = Field(min_length=1)
    board_code: Optional[str] = None
    provider: ProviderMetadata


class ConceptConstituentRecord(ContractModel):
    """Normalized raw concept constituent record from a market data provider."""

    concept_name: str = Field(min_length=1)
    raw_symbol: str = Field(min_length=1)
    symbol: str = Field(pattern=SYMBOL_PATTERN)
    name: str = Field(min_length=1)
    market: Market = "cn_a"
    exchange: Exchange
    industry: Optional[str] = None
    provider: ProviderMetadata


class MarketDataCompany(ContractModel):
    """Provider-agnostic company record used before evidence enrichment."""

    symbol: str = Field(pattern=SYMBOL_PATTERN)
    name: str = Field(min_length=1)
    market: Market = "cn_a"
    exchange: Exchange
    industry: Optional[str] = None
    concepts: list[str] = Field(default_factory=list)
    provider: ProviderMetadata


class BusinessProfileRecord(ContractModel):
    """Normalized business profile record from a market data provider."""

    raw_symbol: str = Field(min_length=1)
    symbol: str = Field(pattern=SYMBOL_PATTERN)
    main_business: Optional[str] = None
    product_type: Optional[str] = None
    product_name: Optional[str] = None
    business_scope: Optional[str] = None
    provider: ProviderMetadata


class FinancialSnapshotRecord(ContractModel):
    """Normalized financial snapshot record from a market data provider."""

    raw_symbol: str = Field(min_length=1)
    symbol: str = Field(pattern=SYMBOL_PATTERN)
    report_period: str = Field(min_length=1)
    metrics: dict[str, str] = Field(min_length=1)
    provider: ProviderMetadata


class RecallMatch(ContractModel):
    """One reason a company was recalled for a query."""

    source: Literal[
        "theme_alias",
        "concept",
        "recall_keyword",
        "provider_concept_board",
    ]
    term: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class RecalledCandidate(ContractModel):
    """A company recalled for a theme query before enrichment and ranking."""

    company: MarketDataCompany
    matches: list[RecallMatch] = Field(min_length=1)
    recall_score: float = Field(ge=0, le=100)
    fixture_company: Optional[FixtureCompany] = None


class CandidateRecallResult(ContractModel):
    """Candidate recall output before enrichment and ranking."""

    normalized_query: str
    matched_aliases: list[str] = Field(default_factory=list)
    matched_concept_boards: list[str] = Field(default_factory=list)
    candidates: list[RecalledCandidate] = Field(default_factory=list)
    pipeline: PipelineStageTrace
    warnings: list[str] = Field(default_factory=list)


class EvidencePackage(ContractModel):
    """Structured evidence package produced before model ranking."""

    symbol: str = Field(pattern=SYMBOL_PATTERN)
    name: str = Field(min_length=1)
    evidence: list[EvidenceItem] = Field(min_length=1)
    missing_kinds: list[EvidenceKind] = Field(default_factory=list)
    data_boundary: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class EnrichedCandidate(ContractModel):
    """Candidate plus evidence package before coarse/deep ranking."""

    company: MarketDataCompany
    matches: list[RecallMatch] = Field(min_length=1)
    recall_score: float = Field(ge=0, le=100)
    evidence_package: EvidencePackage
    fixture_company: Optional[FixtureCompany] = None


class EvidenceEnrichmentResult(ContractModel):
    """Evidence enrichment output before model ranking."""

    normalized_query: str
    candidates: list[EnrichedCandidate] = Field(default_factory=list)
    pipeline: PipelineStageTrace
    data_boundary: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class CoarseRankDecision(ContractModel):
    """Structured coarse-rank decision returned by a model client."""

    symbol: str = Field(pattern=SYMBOL_PATTERN)
    coarse_score: float = Field(ge=0, le=100)
    keep: bool
    reason: str = Field(min_length=1)
    risk_summary: str = Field(min_length=1)
    supporting_evidence_ids: list[str] = Field(min_length=1)


class CoarseRankedCandidate(ContractModel):
    """Candidate plus coarse-rank model decision before deep ranking."""

    candidate: EnrichedCandidate
    decision: CoarseRankDecision


class CoarseRankResult(ContractModel):
    """Coarse ranking output before final ranking and report generation."""

    normalized_query: str
    model_spec: ModelSpec
    candidates: list[CoarseRankedCandidate] = Field(default_factory=list)
    pipeline: PipelineStageTrace
    data_boundary: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class DeepRankDecision(ContractModel):
    """Structured final ranking decision returned by a model client."""

    symbol: str = Field(pattern=SYMBOL_PATTERN)
    final_score: float = Field(ge=0, le=100)
    rank: Optional[int] = Field(default=None, ge=1)
    final_reason: str = Field(min_length=1)
    risk_assessment: str = Field(min_length=1)
    uncertainty: str = Field(min_length=1)
    supporting_evidence_ids: list[str] = Field(min_length=1)
    key_risks: list[str] = Field(min_length=1)


class DeepRankedCandidate(ContractModel):
    """Candidate plus final ranking decision before report generation."""

    candidate: CoarseRankedCandidate
    decision: DeepRankDecision


class DeepRankResult(ContractModel):
    """Final model ranking output before report generation."""

    normalized_query: str
    model_spec: ModelSpec
    candidates: list[DeepRankedCandidate] = Field(default_factory=list)
    pipeline: PipelineStageTrace
    data_boundary: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

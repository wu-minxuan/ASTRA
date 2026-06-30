"""Evidence enrichment for Phase 1 theme research candidates."""

from __future__ import annotations

from collections.abc import Sequence

from astra.theme_research.contracts import (
    BusinessProfileRecord,
    CandidateRecallResult,
    EnrichedCandidate,
    EvidenceEnrichmentResult,
    EvidenceItem,
    EvidenceKind,
    EvidencePackage,
    EvidenceSourceType,
    FinancialSnapshotRecord,
    FixtureCompany,
    PipelineStageTrace,
    ProviderMetadata,
    RecalledCandidate,
)
from astra.theme_research.market_data import MarketDataProvider

DEFAULT_REQUIRED_EVIDENCE_KINDS: tuple[EvidenceKind, ...] = (
    "concept",
    "industry",
    "business_summary",
    "financial_summary",
    "text_summary",
    "risk",
    "theme_relationship",
)
WEB_KNOWLEDGE_BOUNDARY = (
    "P1-T07 did not query WebKnowledgeProvider; real web, news, announcement, "
    "or research-report text evidence is not available in this stage."
)


def enrich_recalled_candidates(
    recall_result: CandidateRecallResult,
    provider: MarketDataProvider | None = None,
    required_kinds: Sequence[EvidenceKind] = DEFAULT_REQUIRED_EVIDENCE_KINDS,
) -> EvidenceEnrichmentResult:
    """Build structured evidence packages for recalled candidates."""
    enriched_candidates = [
        enrich_recalled_candidate(candidate, provider, required_kinds)
        for candidate in recall_result.candidates
    ]
    warnings = _deduplicate_strings(
        [
            *recall_result.warnings,
            *(
                warning
                for candidate in enriched_candidates
                for warning in candidate.evidence_package.warnings
            ),
        ]
    )
    data_boundary = _deduplicate_strings(
        [
            WEB_KNOWLEDGE_BOUNDARY,
            *(
                boundary
                for candidate in enriched_candidates
                for boundary in candidate.evidence_package.data_boundary
            ),
        ]
    )
    pipeline = PipelineStageTrace(
        stage="evidence_enrichment",
        input_count=len(recall_result.candidates),
        output_count=len(enriched_candidates),
        notes=[
            f"normalized_query={recall_result.normalized_query}",
            "market data provider and fixture evidence were normalized into evidence packages",
            "web knowledge provider was not used",
        ],
    )
    return EvidenceEnrichmentResult(
        normalized_query=recall_result.normalized_query,
        candidates=enriched_candidates,
        pipeline=pipeline,
        data_boundary=data_boundary,
        warnings=warnings,
    )


def enrich_recalled_candidate(
    candidate: RecalledCandidate,
    provider: MarketDataProvider | None = None,
    required_kinds: Sequence[EvidenceKind] = DEFAULT_REQUIRED_EVIDENCE_KINDS,
) -> EnrichedCandidate:
    """Build one enriched candidate without ranking or report generation."""
    evidence = list(candidate.fixture_company.evidence) if candidate.fixture_company else []
    warnings: list[str] = []
    data_boundary = [_provider_boundary(candidate.company.provider)]

    _append_generated_evidence(evidence, _theme_relationship_evidence(candidate))
    _append_generated_evidence(evidence, _concept_evidence(candidate))
    _append_generated_evidence(evidence, _industry_evidence(candidate))

    if candidate.fixture_company is not None:
        _append_fixture_summary_evidence(evidence, candidate.fixture_company)
        data_boundary.append(
            "Fixture evidence is deterministic test data and does not represent "
            "real-time market facts."
        )
    elif provider is not None:
        _append_provider_business_evidence(evidence, candidate, provider, warnings)
        _append_provider_financial_evidence(evidence, candidate, provider, warnings)
    else:
        warnings.append(
            "market data provider not configured for evidence enrichment: "
            f"{candidate.company.symbol}"
        )

    missing_kinds = [
        kind
        for kind in required_kinds
        if not any(item.kind == kind for item in evidence)
    ]
    if missing_kinds:
        missing_text = ", ".join(missing_kinds)
        warnings.append(f"evidence kinds missing for {candidate.company.symbol}: {missing_text}")
        data_boundary.append(
            f"{candidate.company.symbol} lacks these P1-T07 evidence kinds: {missing_text}."
        )
    if "text_summary" in missing_kinds:
        data_boundary.append(WEB_KNOWLEDGE_BOUNDARY)

    package = EvidencePackage(
        symbol=candidate.company.symbol,
        name=candidate.company.name,
        evidence=evidence,
        missing_kinds=missing_kinds,
        data_boundary=_deduplicate_strings(data_boundary),
        warnings=_deduplicate_strings(warnings),
    )
    return EnrichedCandidate(
        company=candidate.company,
        matches=candidate.matches,
        signals=candidate.signals,
        recall_score=candidate.recall_score,
        recall_assessment=candidate.recall_assessment,
        evidence_package=package,
        fixture_company=candidate.fixture_company,
    )


def _theme_relationship_evidence(candidate: RecalledCandidate) -> EvidenceItem:
    reasons = "；".join(match.reason for match in candidate.matches)
    return EvidenceItem(
        id=_evidence_id(candidate.company.symbol, "theme_relationship", "recall"),
        kind="theme_relationship",
        stance="inference",
        summary=f"召回阶段保留该候选，匹配依据：{reasons}",
        source_name=_source_name(candidate.company.provider),
        source_type=_source_type(candidate.company.provider),
        source_date=_source_date(candidate.company.provider),
        source_url=None,
        confidence="medium",
    )


def _concept_evidence(candidate: RecalledCandidate) -> EvidenceItem | None:
    if not candidate.company.concepts:
        return None
    concepts = "、".join(candidate.company.concepts)
    return EvidenceItem(
        id=_evidence_id(candidate.company.symbol, "concept", "provider"),
        kind="concept",
        stance="fact",
        summary=f"候选公司出现在以下概念或板块字段中：{concepts}。",
        source_name=_source_name(candidate.company.provider),
        source_type=_source_type(candidate.company.provider),
        source_date=_source_date(candidate.company.provider),
        source_url=None,
        confidence=_provider_confidence(candidate.company.provider),
    )


def _industry_evidence(candidate: RecalledCandidate) -> EvidenceItem | None:
    if not candidate.company.industry:
        return None
    return EvidenceItem(
        id=_evidence_id(candidate.company.symbol, "industry", "provider"),
        kind="industry",
        stance="fact",
        summary=f"候选公司行业字段为：{candidate.company.industry}。",
        source_name=_source_name(candidate.company.provider),
        source_type=_source_type(candidate.company.provider),
        source_date=_source_date(candidate.company.provider),
        source_url=None,
        confidence=_provider_confidence(candidate.company.provider),
    )


def _append_fixture_summary_evidence(
    evidence: list[EvidenceItem],
    company: FixtureCompany,
) -> None:
    generated = [
        EvidenceItem(
            id=_evidence_id(company.symbol, "business_summary", "fixture"),
            kind="business_summary",
            stance="assumption",
            summary=company.business_summary,
            source_name="ASTRA Phase 1 fixture",
            source_type="fixture",
            source_date=None,
            source_url=None,
            confidence="high",
        ),
        EvidenceItem(
            id=_evidence_id(company.symbol, "financial_summary", "fixture"),
            kind="financial_summary",
            stance="assumption",
            summary=company.financial_summary,
            source_name="ASTRA Phase 1 fixture",
            source_type="fixture",
            source_date=None,
            source_url=None,
            confidence="medium",
        ),
        EvidenceItem(
            id=_evidence_id(company.symbol, "text_summary", "fixture"),
            kind="text_summary",
            stance="assumption",
            summary=company.text_summary,
            source_name="ASTRA Phase 1 fixture",
            source_type="fixture",
            source_date=None,
            source_url=None,
            confidence="medium",
        ),
        EvidenceItem(
            id=_evidence_id(company.symbol, "risk", "fixture"),
            kind="risk",
            stance="assumption",
            summary=f"样例风险：{'；'.join(company.risks)}。",
            source_name="ASTRA Phase 1 fixture",
            source_type="fixture",
            source_date=None,
            source_url=None,
            confidence="medium",
        ),
    ]
    for item in generated:
        _append_if_kind_missing(evidence, item)


def _append_provider_business_evidence(
    evidence: list[EvidenceItem],
    candidate: RecalledCandidate,
    provider: MarketDataProvider,
    warnings: list[str],
) -> None:
    try:
        profile = provider.get_business_profile(candidate.company.symbol)
    except Exception as exc:
        warnings.append(
            f"business profile unavailable for {candidate.company.symbol}: {exc}"
        )
        return
    _append_generated_evidence(evidence, _business_profile_evidence(profile))


def _append_provider_financial_evidence(
    evidence: list[EvidenceItem],
    candidate: RecalledCandidate,
    provider: MarketDataProvider,
    warnings: list[str],
) -> None:
    try:
        snapshot = provider.get_financial_snapshot(candidate.company.symbol)
    except Exception as exc:
        warnings.append(
            f"financial snapshot unavailable for {candidate.company.symbol}: {exc}"
        )
        return
    _append_generated_evidence(evidence, _financial_snapshot_evidence(snapshot))


def _business_profile_evidence(profile: BusinessProfileRecord) -> EvidenceItem:
    parts = []
    if profile.main_business:
        parts.append(f"主营业务：{profile.main_business}")
    if profile.product_type:
        parts.append(f"产品类型：{profile.product_type}")
    if profile.product_name:
        parts.append(f"产品名称：{profile.product_name}")
    if profile.business_scope:
        parts.append(f"经营范围：{profile.business_scope}")
    return EvidenceItem(
        id=_evidence_id(profile.symbol, "business_summary", "provider"),
        kind="business_summary",
        stance="fact",
        summary="；".join(parts),
        source_name=_source_name(profile.provider),
        source_type="market_data_provider",
        source_date=_source_date(profile.provider),
        source_url=None,
        confidence="medium",
    )


def _financial_snapshot_evidence(snapshot: FinancialSnapshotRecord) -> EvidenceItem:
    metrics = "；".join(f"{name}={value}" for name, value in snapshot.metrics.items())
    return EvidenceItem(
        id=_evidence_id(snapshot.symbol, "financial_summary", "provider"),
        kind="financial_summary",
        stance="fact",
        summary=f"AKShare 财务摘要在 {snapshot.report_period} 提供指标：{metrics}。",
        source_name=_source_name(snapshot.provider),
        source_type="market_data_provider",
        source_date=_report_period_to_date(snapshot.report_period)
        or _source_date(snapshot.provider),
        source_url=None,
        confidence="medium",
    )


def _append_generated_evidence(
    evidence: list[EvidenceItem],
    item: EvidenceItem | None,
) -> None:
    if item is None:
        return
    existing_ids = {existing.id for existing in evidence}
    if item.id not in existing_ids:
        evidence.append(item)


def _append_if_kind_missing(evidence: list[EvidenceItem], item: EvidenceItem) -> None:
    if not any(existing.kind == item.kind for existing in evidence):
        evidence.append(item)


def _provider_boundary(metadata: ProviderMetadata) -> str:
    if metadata.provider_name == "fixture":
        return "Candidate evidence includes fixture data for deterministic local validation."
    if metadata.provider_interface.startswith("market_metadata_cache:"):
        failure = (
            f"; live_failure={metadata.failure_reason}"
            if metadata.failure_reason
            else ""
        )
        return (
            f"Candidate evidence uses {metadata.provider_name} cached market metadata "
            f"snapshot from {metadata.provider_interface}; "
            f"retrieved_at={metadata.retrieved_at}{failure}."
        )
    fallback = " with fallback" if metadata.is_fallback else ""
    return (
        f"Candidate evidence includes {metadata.provider_name} market data from "
        f"{metadata.provider_interface}{fallback}; retrieved_at={metadata.retrieved_at}."
    )


def _source_type(metadata: ProviderMetadata) -> EvidenceSourceType:
    if metadata.provider_name == "fixture":
        return "fixture"
    return "market_data_provider"


def _source_name(metadata: ProviderMetadata) -> str:
    if metadata.provider_name == "fixture":
        return "ASTRA Phase 1 fixture"
    return f"{metadata.provider_name}:{metadata.provider_interface}"


def _source_date(metadata: ProviderMetadata) -> str | None:
    retrieved_at = metadata.retrieved_at
    if len(retrieved_at) >= 10:
        candidate = retrieved_at[:10]
        if _is_contract_date(candidate):
            return candidate
    return None


def _report_period_to_date(report_period: str) -> str | None:
    if len(report_period) != 8 or not report_period.isdigit():
        return None
    return f"{report_period[:4]}-{report_period[4:6]}-{report_period[6:]}"


def _is_contract_date(value: str) -> bool:
    parts = value.split("-")
    return (
        len(parts) == 3
        and len(parts[0]) == 4
        and len(parts[1]) == 2
        and len(parts[2]) == 2
        and all(part.isdigit() for part in parts)
    )


def _provider_confidence(metadata: ProviderMetadata) -> str:
    return "medium" if metadata.provider_name != "fixture" or metadata.is_fallback else "high"


def _evidence_id(symbol: str, kind: EvidenceKind, suffix: str) -> str:
    stable_symbol = symbol.casefold().replace(".", "-")
    return f"p1t07-{stable_symbol}-{kind}-{suffix}"


def _deduplicate_strings(values: Sequence[str]) -> list[str]:
    deduplicated: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value and value not in seen:
            deduplicated.append(value)
            seen.add(value)
    return deduplicated

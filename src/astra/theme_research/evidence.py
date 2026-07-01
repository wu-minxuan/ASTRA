"""Evidence enrichment for Phase 1 theme research candidates."""

from __future__ import annotations

import hashlib
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
    FinancialStatementRecord,
    FinancialStatementType,
    FixtureCompany,
    PipelineStageTrace,
    ProviderMetadata,
    RecalledCandidate,
    WebKnowledgeRecord,
)
from astra.theme_research.market_data import MarketDataProvider
from astra.theme_research.web_knowledge import WebKnowledgeProvider

DEFAULT_REQUIRED_EVIDENCE_KINDS: tuple[EvidenceKind, ...] = (
    "concept",
    "industry",
    "business_summary",
    "financial_summary",
    "financial_statement",
    "text_summary",
    "risk",
    "theme_relationship",
)
WEB_KNOWLEDGE_BOUNDARY = (
    "WebKnowledgeProvider was not configured for this evidence enrichment run; "
    "real web, news, announcement, or research-report text evidence may be missing."
)
FINANCIAL_STATEMENT_TYPES: tuple[FinancialStatementType, ...] = (
    "balance_sheet",
    "income_statement",
    "cash_flow_statement",
)
FINANCIAL_STATEMENT_LABELS: dict[FinancialStatementType, str] = {
    "balance_sheet": "资产负债表",
    "income_statement": "利润表",
    "cash_flow_statement": "现金流量表",
}
WEB_RISK_TERMS = (
    "风险",
    "处罚",
    "诉讼",
    "仲裁",
    "退市",
    "立案",
    "监管",
    "减持",
    "亏损",
)


def enrich_recalled_candidates(
    recall_result: CandidateRecallResult,
    provider: MarketDataProvider | None = None,
    web_knowledge_provider: WebKnowledgeProvider | None = None,
    required_kinds: Sequence[EvidenceKind] = DEFAULT_REQUIRED_EVIDENCE_KINDS,
) -> EvidenceEnrichmentResult:
    """Build structured evidence packages for recalled candidates."""
    enriched_candidates = [
        enrich_recalled_candidate(
            candidate,
            provider,
            required_kinds,
            web_knowledge_provider=web_knowledge_provider,
            normalized_query=recall_result.normalized_query,
        )
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
            "market data provider, fixture data, and optional web knowledge records "
            "were normalized into evidence packages",
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
    *,
    web_knowledge_provider: WebKnowledgeProvider | None = None,
    normalized_query: str = "",
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
        _append_fixture_financial_statement_evidence(evidence, candidate.fixture_company)
        data_boundary.append(
            "Fixture evidence is deterministic test data and does not represent "
            "real-time market facts."
        )
    elif provider is not None:
        _append_provider_business_evidence(evidence, candidate, provider, warnings)
        _append_provider_financial_evidence(evidence, candidate, provider, warnings)
        _append_provider_financial_statement_evidence(
            evidence,
            candidate,
            provider,
            warnings,
        )
    else:
        warnings.append(
            "market data provider not configured for evidence enrichment: "
            f"{candidate.company.symbol}"
        )

    if web_knowledge_provider is not None:
        _append_web_knowledge_evidence(
            evidence,
            candidate,
            normalized_query,
            web_knowledge_provider,
            warnings,
            data_boundary,
        )
    else:
        data_boundary.append(WEB_KNOWLEDGE_BOUNDARY)

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


def _append_fixture_financial_statement_evidence(
    evidence: list[EvidenceItem],
    company: FixtureCompany,
) -> None:
    for statement_type in FINANCIAL_STATEMENT_TYPES:
        label = FINANCIAL_STATEMENT_LABELS[statement_type]
        _append_generated_evidence(
            evidence,
            EvidenceItem(
                id=_evidence_id(company.symbol, "financial_statement", statement_type),
                kind="financial_statement",
                stance="assumption",
                summary=f"样例 {label}：{company.financial_summary}",
                source_name="ASTRA Phase 1 fixture",
                source_type="fixture",
                source_title=f"ASTRA fixture {label}",
                source_date=None,
                source_url=None,
                retrieved_at=None,
                confidence="low",
                attributes={
                    "statement_type": statement_type,
                    "fixture_financial_summary": company.financial_summary,
                },
            ),
        )


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


def _append_provider_financial_statement_evidence(
    evidence: list[EvidenceItem],
    candidate: RecalledCandidate,
    provider: MarketDataProvider,
    warnings: list[str],
) -> None:
    for statement_type in FINANCIAL_STATEMENT_TYPES:
        try:
            statement = provider.get_financial_statement(candidate.company.symbol, statement_type)
        except Exception as exc:
            warnings.append(
                "financial statement unavailable for "
                f"{candidate.company.symbol}: {statement_type}: {exc}"
            )
            continue
        _append_generated_evidence(evidence, _financial_statement_evidence(statement))


def _append_web_knowledge_evidence(
    evidence: list[EvidenceItem],
    candidate: RecalledCandidate,
    normalized_query: str,
    web_knowledge_provider: WebKnowledgeProvider,
    warnings: list[str],
    data_boundary: list[str],
) -> None:
    try:
        result = web_knowledge_provider.search_company_knowledge(
            symbol=candidate.company.symbol,
            theme=normalized_query,
        )
    except Exception as exc:
        warnings.append(
            f"web knowledge unavailable for {candidate.company.symbol}: {exc}"
        )
        data_boundary.append(
            f"{candidate.company.symbol} web knowledge provider failed: {exc}."
        )
        return

    warnings.extend(result.warnings)
    if not result.records:
        warnings.append(f"web knowledge records empty for {candidate.company.symbol}")
        data_boundary.append(
            f"{candidate.company.symbol} has no usable WebKnowledgeProvider records."
        )
        return
    for record in result.records:
        _append_generated_evidence(evidence, _web_knowledge_evidence(record))
    data_boundary.append(
        f"{candidate.company.symbol} includes {len(result.records)} web knowledge "
        "records from WebKnowledgeProvider."
    )


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
        source_title="AKShare 主营业务资料",
        source_date=_source_date(profile.provider),
        source_url=None,
        retrieved_at=profile.provider.retrieved_at,
        confidence="medium",
        attributes={
            "main_business": profile.main_business,
            "product_type": profile.product_type,
            "product_name": profile.product_name,
            "business_scope": profile.business_scope,
        },
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
        source_title="AKShare 财务摘要",
        source_date=_report_period_to_date(snapshot.report_period)
        or _source_date(snapshot.provider),
        source_url=None,
        retrieved_at=snapshot.provider.retrieved_at,
        confidence="medium",
        attributes={
            "report_period": snapshot.report_period,
            "metrics": dict(snapshot.metrics),
        },
    )


def _financial_statement_evidence(statement: FinancialStatementRecord) -> EvidenceItem:
    label = FINANCIAL_STATEMENT_LABELS[statement.statement_type]
    latest_report_date = _latest_report_date(statement)
    return EvidenceItem(
        id=_evidence_id(
            statement.symbol,
            "financial_statement",
            statement.statement_type,
        ),
        kind="financial_statement",
        stance="fact",
        summary=(
            f"AKShare 完整{label}按报告期返回 {len(statement.rows)} 行、"
            f"{len(statement.columns)} 个字段"
            f"{f'，最新报告期 {latest_report_date}' if latest_report_date else ''}。"
        ),
        source_name=_source_name(statement.provider),
        source_type="market_data_provider",
        source_title=f"AKShare 完整{label}",
        source_date=_contract_date(latest_report_date) or _source_date(statement.provider),
        source_url=None,
        retrieved_at=statement.provider.retrieved_at,
        confidence="medium" if not statement.provider.is_fallback else "low",
        attributes={
            "statement_type": statement.statement_type,
            "report_basis": statement.report_basis,
            "columns": list(statement.columns),
            "rows": list(statement.rows),
            "row_count": len(statement.rows),
            "latest_report_date": latest_report_date,
        },
    )


def _web_knowledge_evidence(record: WebKnowledgeRecord) -> EvidenceItem:
    return EvidenceItem(
        id=_evidence_id(
            record.symbol,
            _web_record_kind(record),
            f"{record.source_type}-{_stable_suffix(record.title)}",
        ),
        kind=_web_record_kind(record),
        stance="fact",
        summary=record.summary,
        source_name=record.source_name,
        source_type=record.source_type,
        source_title=record.title,
        source_date=record.published_at,
        source_url=record.source_url,
        retrieved_at=record.retrieved_at,
        confidence=record.confidence,
        attributes=dict(record.attributes),
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


def _latest_report_date(statement: FinancialStatementRecord) -> str | None:
    for row in statement.rows:
        value = row.get("REPORT_DATE") or row.get("报告日期") or row.get("report_date")
        if value is not None:
            return str(value)
    return None


def _contract_date(value: str | None) -> str | None:
    if not value or len(value) < 10:
        return None
    candidate = value[:10]
    if _is_contract_date(candidate):
        return candidate
    return None


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


def _web_record_kind(record: WebKnowledgeRecord) -> EvidenceKind:
    if record.source_type == "public_disclosure":
        checked_text = f"{record.title} {record.summary}"
        if any(term in checked_text for term in WEB_RISK_TERMS):
            return "risk"
    return "text_summary"


def _stable_suffix(value: str) -> str:
    lowered = value.casefold()
    characters = [
        character
        for character in lowered
        if character.isascii() and character.isalnum()
    ]
    if characters:
        return "".join(characters[:24])
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:12]


def _deduplicate_strings(values: Sequence[str]) -> list[str]:
    deduplicated: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value and value not in seen:
            deduplicated.append(value)
            seen.add(value)
    return deduplicated

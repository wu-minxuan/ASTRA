"""Application service for running the Phase 1 theme research funnel."""

from __future__ import annotations

from datetime import date
from typing import Any

from astra.theme_research.coarse_rank import ModelClient, coarse_rank_candidates
from astra.theme_research.contracts import (
    CandidateRecallResult,
    NormalizedThemeRequest,
    ThemeResearchErrorCode,
    ThemeResearchRequest,
    ThemeResearchResponse,
    ThemeResearchResult,
)
from astra.theme_research.deep_rank import deep_rank_candidates
from astra.theme_research.evidence import enrich_recalled_candidates
from astra.theme_research.market_data import AkshareMarketDataProvider, MarketDataProvider
from astra.theme_research.market_metadata import (
    MarketMetadataBackedProvider,
    MarketMetadataStore,
)
from astra.theme_research.recall import recall_candidates_from_provider
from astra.theme_research.report import (
    candidate_stock_from_deep_ranked,
    generate_theme_research_result,
)

PROVIDER_UNAVAILABLE_WARNING_MARKERS = (
    "call failed",
    "failed",
    "timeout",
    "timed out",
    "connection",
    "function not available",
    "not available",
    "remote end closed",
)


class ThemeResearchServiceError(RuntimeError):
    """Structured service error that can be mapped to the API error contract."""

    def __init__(
        self,
        code: ThemeResearchErrorCode,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


def run_theme_research(
    request: ThemeResearchRequest,
    *,
    market_data_provider: MarketDataProvider | None = None,
    market_metadata_store: MarketMetadataStore | None = None,
    coarse_model_client: ModelClient | None = None,
    deep_model_client: ModelClient | None = None,
    report_model_client: ModelClient | None = None,
) -> ThemeResearchResponse:
    """Run the Phase 1 research funnel against the configured market data provider."""
    provider = market_data_provider or MarketMetadataBackedProvider(
        AkshareMarketDataProvider(),
        metadata_store=market_metadata_store,
    )
    recall_result = recall_candidates_from_provider(
        request.theme,
        provider,
        fallback_dataset=None,
    )
    if not recall_result.candidates:
        _raise_empty_recall_error(request, recall_result, provider)

    enrichment_result = enrich_recalled_candidates(recall_result, provider=provider)
    coarse_result = coarse_rank_candidates(
        enrichment_result,
        model_client=coarse_model_client,
    )
    deep_result = deep_rank_candidates(
        coarse_result,
        model_client=deep_model_client,
        max_results=request.max_results,
    )
    if not deep_result.candidates:
        raise ThemeResearchServiceError(
            "no_candidates",
            f"主题 `{request.theme}` 的候选股票未通过模型排序筛选。",
            {
                "normalized_query": recall_result.normalized_query,
                "provider": _provider_name(provider),
                "warnings": list(deep_result.warnings),
            },
        )

    pipeline = [
        recall_result.pipeline,
        enrichment_result.pipeline,
        coarse_result.pipeline,
        deep_result.pipeline,
    ]
    as_of = date.today().isoformat()
    if request.include_report:
        result = generate_theme_research_result(
            deep_result,
            as_of=as_of,
            model_client=report_model_client,
        )
        pipeline = [*pipeline, result.pipeline[-1]]
        result = result.model_copy(update={"pipeline": pipeline})
    else:
        result = ThemeResearchResult(
            as_of=as_of,
            pool=[
                candidate_stock_from_deep_ranked(candidate)
                for candidate in deep_result.candidates
            ],
            report=None,
            pipeline=pipeline,
            data_boundary=list(deep_result.data_boundary),
            warnings=list(deep_result.warnings),
        )

    return ThemeResearchResponse(
        request=NormalizedThemeRequest(
            theme=request.theme,
            normalized_query=recall_result.normalized_query,
            market=request.market,
            max_results=request.max_results,
            include_report=request.include_report,
        ),
        result=result,
    )


def _raise_empty_recall_error(
    request: ThemeResearchRequest,
    recall_result: CandidateRecallResult,
    provider: MarketDataProvider,
) -> None:
    provider_warnings = [
        warning
        for warning in recall_result.warnings
        if _looks_like_provider_unavailable(warning)
    ]
    details = {
        "normalized_query": recall_result.normalized_query,
        "provider": _provider_name(provider),
        "stage": "candidate_recall",
        "warnings": list(recall_result.warnings),
    }

    if provider_warnings:
        raise ThemeResearchServiceError(
            "provider_unavailable",
            f"AKShare 候选召回接口不可用，无法为主题 `{request.theme}` 生成真实股票池。",
            {
                **details,
                "error_message": provider_warnings[0],
            },
        )

    raise ThemeResearchServiceError(
        "no_candidates",
        f"未找到与主题 `{request.theme}` 匹配的候选股票。",
        details,
    )


def _looks_like_provider_unavailable(warning: str) -> bool:
    normalized = warning.casefold()
    if "concept board discovery unavailable" in normalized:
        return True
    if "concept constituents unavailable" in normalized and "returned no records" in normalized:
        return False
    return any(marker in normalized for marker in PROVIDER_UNAVAILABLE_WARNING_MARKERS)


def _provider_name(provider: MarketDataProvider) -> str:
    if isinstance(provider, (AkshareMarketDataProvider, MarketMetadataBackedProvider)):
        return "akshare"
    return provider.__class__.__name__

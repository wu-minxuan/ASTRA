"""Application service for running the Phase 1 theme research funnel."""

from __future__ import annotations

from typing import Any

from astra.theme_research.coarse_rank import ModelClient, coarse_rank_candidates
from astra.theme_research.contracts import (
    NormalizedThemeRequest,
    ThemeResearchErrorCode,
    ThemeResearchRequest,
    ThemeResearchResponse,
    ThemeResearchResult,
)
from astra.theme_research.deep_rank import deep_rank_candidates
from astra.theme_research.evidence import enrich_recalled_candidates
from astra.theme_research.fixtures import load_low_altitude_economy_fixture
from astra.theme_research.recall import recall_candidates
from astra.theme_research.report import (
    candidate_stock_from_deep_ranked,
    generate_theme_research_result,
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
    coarse_model_client: ModelClient | None = None,
    deep_model_client: ModelClient | None = None,
    report_model_client: ModelClient | None = None,
) -> ThemeResearchResponse:
    """Run the deterministic Phase 1 fixture-backed research funnel."""
    dataset = load_low_altitude_economy_fixture()
    recall_result = recall_candidates(request.theme, dataset)
    if not recall_result.candidates:
        raise ThemeResearchServiceError(
            "no_candidates",
            f"未找到与主题 `{request.theme}` 匹配的候选股票。",
            {"normalized_query": recall_result.normalized_query},
        )

    enrichment_result = enrich_recalled_candidates(recall_result)
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
            {"normalized_query": recall_result.normalized_query},
        )

    pipeline = [
        recall_result.pipeline,
        enrichment_result.pipeline,
        coarse_result.pipeline,
        deep_result.pipeline,
    ]
    if request.include_report:
        result = generate_theme_research_result(
            deep_result,
            as_of=dataset.as_of,
            model_client=report_model_client,
        )
        pipeline = [*pipeline, result.pipeline[-1]]
        result = result.model_copy(update={"pipeline": pipeline})
    else:
        result = ThemeResearchResult(
            as_of=dataset.as_of,
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

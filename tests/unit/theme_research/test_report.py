from collections.abc import Mapping

import pytest

from astra.theme_research.coarse_rank import (
    FakeCoarseRankModelClient,
    ModelOutputValidationError,
    ModelSafetyError,
    coarse_rank_candidates,
)
from astra.theme_research.contracts import ModelSpec
from astra.theme_research.deep_rank import FakeDeepRankModelClient, deep_rank_candidates
from astra.theme_research.evidence import enrich_recalled_candidates
from astra.theme_research.fixtures import load_low_altitude_economy_fixture
from astra.theme_research.recall import recall_candidates
from astra.theme_research.report import (
    NOT_INVESTMENT_ADVICE,
    FakeReportGenerationModelClient,
    generate_theme_research_result,
)


def make_deep_result():
    dataset = load_low_altitude_economy_fixture()
    recall_result = recall_candidates("低空经济", dataset)
    enrichment_result = enrich_recalled_candidates(recall_result)
    coarse_result = coarse_rank_candidates(
        enrichment_result,
        model_client=FakeCoarseRankModelClient(),
        model_spec=ModelSpec(
            provider_name="fake",
            model_name="unit-test-coarse-model",
            purpose="coarse_rank",
            prompt_version="unit-test-coarse-prompt",
        ),
    )
    return deep_rank_candidates(
        coarse_result,
        model_client=FakeDeepRankModelClient(),
        model_spec=ModelSpec(
            provider_name="fake",
            model_name="unit-test-deep-model",
            purpose="deep_rank",
            prompt_version="unit-test-deep-prompt",
        ),
    )


def make_model_spec() -> ModelSpec:
    return ModelSpec(
        provider_name="fake",
        model_name="unit-test-report-model",
        purpose="report_generation",
        prompt_version="unit-test-report-prompt",
    )


class InvalidReportClient:
    def generate_structured(
        self,
        *,
        model_spec: ModelSpec,
        schema_name: str,
        payload: Mapping[str, object],
    ) -> Mapping[str, object]:
        return {
            "title": "",
            "summary": "摘要。",
            "theme_overview": "主题概述。",
            "pool_summary": "股票池摘要。",
            "focus_companies": [],
            "risks": [],
            "data_boundary": "边界。",
            "not_investment_advice": NOT_INVESTMENT_ADVICE,
        }


class UnknownEvidenceReportClient:
    def generate_structured(
        self,
        *,
        model_spec: ModelSpec,
        schema_name: str,
        payload: Mapping[str, object],
    ) -> Mapping[str, object]:
        focus_companies = list(payload["focus_companies"])
        first_focus = dict(focus_companies[0])
        first_focus["supporting_evidence_ids"] = ["missing-evidence-id"]
        focus_companies[0] = first_focus
        return {
            "title": "低空经济主题股票池研究报告",
            "summary": "摘要。",
            "theme_overview": "主题概述。",
            "pool_summary": "股票池摘要。",
            "focus_companies": focus_companies,
            "risks": ["风险。"],
            "data_boundary": "边界。",
            "not_investment_advice": NOT_INVESTMENT_ADVICE,
        }


class TradingDirectiveReportClient:
    def generate_structured(
        self,
        *,
        model_spec: ModelSpec,
        schema_name: str,
        payload: Mapping[str, object],
    ) -> Mapping[str, object]:
        return {
            "title": "低空经济主题股票池研究报告",
            "summary": "建议买入排名靠前公司。",
            "theme_overview": "主题概述。",
            "pool_summary": "股票池摘要。",
            "focus_companies": payload["focus_companies"],
            "risks": ["风险。"],
            "data_boundary": "边界。",
            "not_investment_advice": NOT_INVESTMENT_ADVICE,
        }


def test_generate_theme_research_result_builds_pool_and_report() -> None:
    deep_result = make_deep_result()

    result = generate_theme_research_result(
        deep_result,
        as_of="2026-06-30",
        model_client=FakeReportGenerationModelClient(),
        model_spec=make_model_spec(),
    )

    assert result.as_of == "2026-06-30"
    assert len(result.pool) == 5
    assert result.report is not None
    assert result.report.title == "低空经济主题股票池研究报告"
    assert result.report.not_investment_advice == NOT_INVESTMENT_ADVICE
    assert "交易建议" in result.report.not_investment_advice
    assert [candidate.rank for candidate in result.pool] == [1, 2, 3, 4, 5]
    assert all(candidate.scores.final_score >= 0 for candidate in result.pool)
    assert all(candidate.evidence for candidate in result.pool)
    assert result.pipeline[-1].stage == "report_generation"
    assert result.pipeline[-1].output_count == 1


def test_report_focus_companies_reference_existing_pool_evidence() -> None:
    deep_result = make_deep_result()

    result = generate_theme_research_result(
        deep_result,
        as_of="2026-06-30",
        model_client=FakeReportGenerationModelClient(),
        model_spec=make_model_spec(),
        max_focus_companies=2,
    )

    assert result.report is not None
    assert len(result.report.focus_companies) == 2
    pool_by_symbol = {candidate.symbol: candidate for candidate in result.pool}
    for focus in result.report.focus_companies:
        evidence_ids = {item.id for item in pool_by_symbol[focus.symbol].evidence}
        assert set(focus.supporting_evidence_ids).issubset(evidence_ids)


def test_report_generation_rejects_invalid_structured_output() -> None:
    deep_result = make_deep_result()

    with pytest.raises(ModelOutputValidationError, match="schema invalid"):
        generate_theme_research_result(
            deep_result,
            as_of="2026-06-30",
            model_client=InvalidReportClient(),
            model_spec=make_model_spec(),
        )


def test_report_generation_rejects_unknown_evidence_references() -> None:
    deep_result = make_deep_result()

    with pytest.raises(ModelOutputValidationError, match="unknown evidence"):
        generate_theme_research_result(
            deep_result,
            as_of="2026-06-30",
            model_client=UnknownEvidenceReportClient(),
            model_spec=make_model_spec(),
        )


def test_report_generation_rejects_trading_directives() -> None:
    deep_result = make_deep_result()

    with pytest.raises(ModelSafetyError, match="trading directive"):
        generate_theme_research_result(
            deep_result,
            as_of="2026-06-30",
            model_client=TradingDirectiveReportClient(),
            model_spec=make_model_spec(),
        )

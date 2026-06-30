from collections.abc import Mapping

import pytest

from astra.theme_research.coarse_rank import (
    COARSE_RANK_SCHEMA_NAME,
    FakeCoarseRankModelClient,
    ModelOutputValidationError,
    ModelSafetyError,
    coarse_rank_candidates,
)
from astra.theme_research.contracts import ModelSpec
from astra.theme_research.evidence import enrich_recalled_candidates
from astra.theme_research.fixtures import load_low_altitude_economy_fixture
from astra.theme_research.recall import recall_candidates


def make_enrichment_result():
    dataset = load_low_altitude_economy_fixture()
    recall_result = recall_candidates("低空经济", dataset)
    return enrich_recalled_candidates(recall_result)


def make_model_spec() -> ModelSpec:
    return ModelSpec(
        provider_name="fake",
        model_name="unit-test-model",
        purpose="coarse_rank",
        prompt_version="unit-test-prompt",
    )


class InvalidSchemaClient:
    def generate_structured(
        self,
        *,
        model_spec: ModelSpec,
        schema_name: str,
        payload: Mapping[str, object],
    ) -> Mapping[str, object]:
        return {
            "symbol": payload["symbol"],
            "coarse_score": 101,
            "keep": True,
            "reason": "结构化输出分数越界。",
            "risk_summary": "风险摘要。",
            "supporting_evidence_ids": payload["evidence_ids"],
        }


class UnknownEvidenceClient:
    def generate_structured(
        self,
        *,
        model_spec: ModelSpec,
        schema_name: str,
        payload: Mapping[str, object],
    ) -> Mapping[str, object]:
        return {
            "symbol": payload["symbol"],
            "coarse_score": 80,
            "keep": True,
            "reason": "引用不存在的证据。",
            "risk_summary": "风险摘要。",
            "supporting_evidence_ids": ["missing-evidence-id"],
        }


class TradingDirectiveClient:
    def generate_structured(
        self,
        *,
        model_spec: ModelSpec,
        schema_name: str,
        payload: Mapping[str, object],
    ) -> Mapping[str, object]:
        return {
            "symbol": payload["symbol"],
            "coarse_score": 80,
            "keep": True,
            "reason": "建议买入该候选。",
            "risk_summary": "风险摘要。",
            "supporting_evidence_ids": _first_evidence_id(payload),
        }


class LowScoreKeepClient:
    def generate_structured(
        self,
        *,
        model_spec: ModelSpec,
        schema_name: str,
        payload: Mapping[str, object],
    ) -> Mapping[str, object]:
        return {
            "symbol": payload["symbol"],
            "coarse_score": 55,
            "keep": True,
            "reason": "模型倾向保留但分数不高。",
            "risk_summary": "风险摘要。",
            "supporting_evidence_ids": _first_evidence_id(payload),
        }


def test_fake_coarse_rank_keeps_strong_candidates_and_filters_weak_candidate() -> None:
    enrichment_result = make_enrichment_result()

    result = coarse_rank_candidates(
        enrichment_result,
        model_client=FakeCoarseRankModelClient(),
        model_spec=make_model_spec(),
    )
    decisions_by_symbol = {
        item.candidate.company.symbol: item.decision
        for item in result.candidates
    }

    assert result.pipeline.stage == "coarse_rank"
    assert result.pipeline.input_count == 6
    assert result.pipeline.output_count == 5
    assert result.model_spec.model_name == "unit-test-model"
    assert decisions_by_symbol["999001.SZ"].keep is True
    assert decisions_by_symbol["999006.SH"].keep is False
    assert decisions_by_symbol["999006.SH"].coarse_score < 60
    assert result.candidates[-1].candidate.company.symbol == "999006.SH"


def test_fake_client_requires_coarse_rank_schema_name() -> None:
    enrichment_result = make_enrichment_result()
    payload = {
        "symbol": enrichment_result.candidates[0].company.symbol,
        "recall_score": enrichment_result.candidates[0].recall_score,
        "evidence_ids": ["evidence-1"],
        "evidence_summaries": ["summary"],
        "missing_kinds": [],
    }

    with pytest.raises(ModelOutputValidationError, match="wrong schema"):
        FakeCoarseRankModelClient().generate_structured(
            model_spec=make_model_spec(),
            schema_name="wrong.schema",
            payload=payload,
        )

    assert COARSE_RANK_SCHEMA_NAME == "phase1.coarse_rank.v1"


def test_coarse_rank_rejects_invalid_structured_output() -> None:
    enrichment_result = make_enrichment_result()

    with pytest.raises(ModelOutputValidationError, match="schema invalid"):
        coarse_rank_candidates(
            enrichment_result,
            model_client=InvalidSchemaClient(),
            model_spec=make_model_spec(),
        )


def test_coarse_rank_rejects_unknown_evidence_references() -> None:
    enrichment_result = make_enrichment_result()

    with pytest.raises(ModelOutputValidationError, match="unknown evidence"):
        coarse_rank_candidates(
            enrichment_result,
            model_client=UnknownEvidenceClient(),
            model_spec=make_model_spec(),
        )


def test_coarse_rank_rejects_trading_directives() -> None:
    enrichment_result = make_enrichment_result()

    with pytest.raises(ModelSafetyError, match="trading directive"):
        coarse_rank_candidates(
            enrichment_result,
            model_client=TradingDirectiveClient(),
            model_spec=make_model_spec(),
        )


def test_coarse_rank_applies_minimum_keep_score_filter() -> None:
    enrichment_result = make_enrichment_result()

    result = coarse_rank_candidates(
        enrichment_result,
        model_client=LowScoreKeepClient(),
        model_spec=make_model_spec(),
        min_keep_score=60,
    )

    assert all(not item.decision.keep for item in result.candidates)
    assert result.pipeline.output_count == 0
    assert "低于保留阈值" in result.candidates[0].decision.reason


def _first_evidence_id(payload: Mapping[str, object]) -> list[str]:
    evidence_ids = payload["evidence_ids"]
    assert isinstance(evidence_ids, list)
    return [str(evidence_ids[0])]

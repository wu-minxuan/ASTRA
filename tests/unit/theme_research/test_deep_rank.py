from collections.abc import Mapping

import pytest

from astra.theme_research.coarse_rank import (
    FakeCoarseRankModelClient,
    ModelOutputValidationError,
    ModelSafetyError,
    coarse_rank_candidates,
)
from astra.theme_research.contracts import ModelSpec
from astra.theme_research.deep_rank import (
    DEEP_RANK_SCHEMA_NAME,
    FakeDeepRankModelClient,
    deep_rank_candidates,
)
from astra.theme_research.evidence import enrich_recalled_candidates
from astra.theme_research.fixtures import load_low_altitude_economy_fixture
from astra.theme_research.recall import recall_candidates


def make_coarse_result():
    dataset = load_low_altitude_economy_fixture()
    recall_result = recall_candidates("低空经济", dataset)
    enrichment_result = enrich_recalled_candidates(recall_result)
    return coarse_rank_candidates(
        enrichment_result,
        model_client=FakeCoarseRankModelClient(),
        model_spec=ModelSpec(
            provider_name="fake",
            model_name="unit-test-coarse-model",
            purpose="coarse_rank",
            prompt_version="unit-test-coarse-prompt",
        ),
    )


def make_model_spec() -> ModelSpec:
    return ModelSpec(
        provider_name="fake",
        model_name="unit-test-deep-model",
        purpose="deep_rank",
        prompt_version="unit-test-deep-prompt",
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
            "final_score": 120,
            "rank": None,
            "final_reason": "结构化输出分数越界。",
            "risk_assessment": "风险判断。",
            "uncertainty": "不确定性说明。",
            "supporting_evidence_ids": payload["evidence_ids"],
            "key_risks": ["风险。"],
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
            "final_score": 80,
            "rank": None,
            "final_reason": "引用不存在的证据。",
            "risk_assessment": "风险判断。",
            "uncertainty": "不确定性说明。",
            "supporting_evidence_ids": ["missing-evidence-id"],
            "key_risks": ["风险。"],
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
            "final_score": 80,
            "rank": None,
            "final_reason": "排序靠前，但不构成研究报告。",
            "risk_assessment": "可以考虑买入。",
            "uncertainty": "不确定性说明。",
            "supporting_evidence_ids": _first_evidence_id(payload),
            "key_risks": ["风险。"],
        }


def test_fake_deep_rank_orders_kept_candidates_and_excludes_filtered_candidate() -> None:
    coarse_result = make_coarse_result()

    result = deep_rank_candidates(
        coarse_result,
        model_client=FakeDeepRankModelClient(),
        model_spec=make_model_spec(),
    )
    symbols = [item.candidate.candidate.company.symbol for item in result.candidates]
    ranks = [item.decision.rank for item in result.candidates]

    assert result.pipeline.stage == "deep_rank"
    assert result.pipeline.input_count == 5
    assert result.pipeline.output_count == 5
    assert result.model_spec.model_name == "unit-test-deep-model"
    assert symbols == [
        "999001.SZ",
        "999002.SZ",
        "999003.SH",
        "999004.SH",
        "999005.SZ",
    ]
    assert "999006.SH" not in symbols
    assert ranks == [1, 2, 3, 4, 5]
    assert all(item.decision.final_score >= 0 for item in result.candidates)
    assert all(item.decision.supporting_evidence_ids for item in result.candidates)


def test_deep_rank_can_limit_results_after_assigning_stable_ranks() -> None:
    coarse_result = make_coarse_result()

    result = deep_rank_candidates(
        coarse_result,
        model_client=FakeDeepRankModelClient(),
        model_spec=make_model_spec(),
        max_results=3,
    )

    assert [item.decision.rank for item in result.candidates] == [1, 2, 3]
    assert result.pipeline.output_count == 3


def test_fake_deep_rank_client_requires_deep_rank_schema_name() -> None:
    coarse_result = make_coarse_result()
    candidate = coarse_result.candidates[0]
    payload = {
        "symbol": candidate.candidate.company.symbol,
        "recall_score": candidate.candidate.recall_score,
        "coarse_score": candidate.decision.coarse_score,
        "evidence_ids": ["evidence-1"],
        "evidence_summaries": ["summary"],
        "missing_kinds": [],
    }

    with pytest.raises(ModelOutputValidationError, match="wrong schema"):
        FakeDeepRankModelClient().generate_structured(
            model_spec=make_model_spec(),
            schema_name="wrong.schema",
            payload=payload,
        )

    assert DEEP_RANK_SCHEMA_NAME == "phase1.deep_rank.v1"


def test_deep_rank_rejects_invalid_structured_output() -> None:
    coarse_result = make_coarse_result()

    with pytest.raises(ModelOutputValidationError, match="schema invalid"):
        deep_rank_candidates(
            coarse_result,
            model_client=InvalidSchemaClient(),
            model_spec=make_model_spec(),
        )


def test_deep_rank_rejects_unknown_evidence_references() -> None:
    coarse_result = make_coarse_result()

    with pytest.raises(ModelOutputValidationError, match="unknown evidence"):
        deep_rank_candidates(
            coarse_result,
            model_client=UnknownEvidenceClient(),
            model_spec=make_model_spec(),
        )


def test_deep_rank_rejects_trading_directives() -> None:
    coarse_result = make_coarse_result()

    with pytest.raises(ModelSafetyError, match="trading directive"):
        deep_rank_candidates(
            coarse_result,
            model_client=TradingDirectiveClient(),
            model_spec=make_model_spec(),
        )


def _first_evidence_id(payload: Mapping[str, object]) -> list[str]:
    evidence_ids = payload["evidence_ids"]
    assert isinstance(evidence_ids, list)
    return [str(evidence_ids[0])]

import pytest
from pydantic import ValidationError

from astra.theme_research.contracts import (
    CONTRACT_VERSION,
    CandidateStock,
    EvidenceItem,
    NormalizedThemeRequest,
    PipelineStageTrace,
    ScoreBreakdown,
    ScoreFactor,
    ThemeResearchError,
    ThemeResearchErrorResponse,
    ThemeResearchRequest,
)


def make_evidence() -> EvidenceItem:
    return EvidenceItem(
        id="evidence-1",
        kind="concept",
        stance="fact",
        summary="固定样例证据。",
        source_name="ASTRA Phase 1 fixture",
        source_type="fixture",
        source_date="2026-06-15",
        source_url=None,
        confidence="high",
    )


def make_score() -> ScoreBreakdown:
    return ScoreBreakdown(
        recall_score=90,
        coarse_score=80,
        final_score=85,
        factors=[ScoreFactor(name="theme_match", value=45, reason="主题匹配度高。")],
    )


def test_theme_research_request_defaults_and_trims_theme() -> None:
    request = ThemeResearchRequest(theme="  低空经济  ")

    assert request.theme == "低空经济"
    assert request.market == "cn_a"
    assert request.max_results == 5
    assert request.include_report is True

    normalized = NormalizedThemeRequest.from_request(request)

    assert normalized.model_dump() == {
        "theme": "低空经济",
        "normalized_query": "低空经济",
        "market": "cn_a",
        "max_results": 5,
        "include_report": True,
    }


@pytest.mark.parametrize(
    "payload",
    [
        {"theme": "   "},
        {"theme": "低空经济", "market": "us"},
        {"theme": "低空经济", "max_results": 0},
        {"theme": "低空经济", "max_results": 11},
    ],
)
def test_theme_research_request_rejects_invalid_input(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        ThemeResearchRequest(**payload)


def test_score_breakdown_rejects_out_of_range_scores() -> None:
    with pytest.raises(ValidationError):
        ScoreBreakdown(
            recall_score=101,
            coarse_score=80,
            final_score=85,
            factors=[ScoreFactor(name="theme_match", value=45, reason="主题匹配度高。")],
        )


def test_pipeline_stage_trace_rejects_unknown_stage() -> None:
    with pytest.raises(ValidationError):
        PipelineStageTrace(stage="unknown", input_count=0, output_count=0)


def test_candidate_stock_accepts_unranked_and_ranked_values() -> None:
    candidate = CandidateStock(
        symbol="999001.SZ",
        name="低空样例一号",
        market="cn_a",
        exchange="SZSE",
        industry="航空装备",
        concepts=["低空经济"],
        recall_sources=["fixture concept match"],
        evidence=[make_evidence()],
        scores=make_score(),
        rank=None,
        selection_reason="尚未进入排序阶段。",
        key_risks=["商业化节奏存在不确定性。"],
    )

    assert candidate.rank is None

    ranked_candidate = candidate.model_copy(update={"rank": 1})

    assert ranked_candidate.rank == 1

    with pytest.raises(ValidationError):
        CandidateStock(**{**candidate.model_dump(), "rank": 0})


def test_error_response_uses_contract_version() -> None:
    response = ThemeResearchErrorResponse(
        error=ThemeResearchError(code="invalid_request", message="theme must not be empty")
    )

    assert response.contract_version == CONTRACT_VERSION
    assert response.model_dump()["error"] == {
        "code": "invalid_request",
        "message": "theme must not be empty",
        "details": {},
    }

"""Deep ranking baseline for Phase 1 theme research."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from pydantic import ValidationError

from astra.theme_research.coarse_rank import (
    TRADING_DIRECTIVE_TERMS,
    ModelClient,
    ModelOutputValidationError,
    ModelSafetyError,
)
from astra.theme_research.contracts import (
    CoarseRankedCandidate,
    CoarseRankResult,
    DeepRankDecision,
    DeepRankedCandidate,
    DeepRankResult,
    EvidenceItem,
    ModelSpec,
    PipelineStageTrace,
)

DEEP_RANK_MODEL_SPEC = ModelSpec(
    provider_name="fake",
    model_name="fake-deep-ranker-v1",
    purpose="deep_rank",
    prompt_version="p1-t09-deep-rank-v1",
    temperature=0.0,
    max_output_tokens=1536,
)
DEEP_RANK_SCHEMA_NAME = "phase1.deep_rank.v1"


class FakeDeepRankModelClient:
    """Deterministic fake deep-rank model client for tests and local development."""

    def generate_structured(
        self,
        *,
        model_spec: ModelSpec,
        schema_name: str,
        payload: Mapping[str, object],
    ) -> Mapping[str, object]:
        if model_spec.purpose != "deep_rank":
            raise ModelOutputValidationError("fake deep ranker received wrong model purpose")
        if schema_name != DEEP_RANK_SCHEMA_NAME:
            raise ModelOutputValidationError("fake deep ranker received wrong schema")

        symbol = str(payload["symbol"])
        recall_score = float(payload["recall_score"])
        coarse_score = float(payload["coarse_score"])
        evidence_ids = _payload_list(payload, "evidence_ids")
        evidence_summaries = _payload_list(payload, "evidence_summaries")
        missing_kinds = _payload_list(payload, "missing_kinds")
        risk_summaries = [
            summary
            for summary in evidence_summaries
            if "|risk|" in summary or "风险" in summary
        ]
        score = (recall_score * 0.35) + (coarse_score * 0.55) + 10
        if missing_kinds:
            score -= min(20, len(missing_kinds) * 4)
        score = max(0, min(100, score))
        return {
            "symbol": symbol,
            "final_score": score,
            "rank": None,
            "final_reason": "精排结论：证据链、召回依据和粗排分共同支持该候选排序。",
            "risk_assessment": (
                _clean_risk_summary(risk_summaries[0])
                if risk_summaries
                else "主要风险来自证据不足或主题相关性不确定。"
            ),
            "uncertainty": (
                f"仍缺少这些证据类型：{', '.join(missing_kinds)}。"
                if missing_kinds
                else "当前排序基于固定证据包和 fake model，不代表真实市场结论。"
            ),
            "supporting_evidence_ids": evidence_ids[:4] or evidence_ids,
            "key_risks": [
                _clean_risk_summary(risk_summaries[0])
                if risk_summaries
                else "证据覆盖不足可能影响排序稳定性。"
            ],
        }


def deep_rank_candidates(
    coarse_result: CoarseRankResult,
    model_client: ModelClient | None = None,
    model_spec: ModelSpec = DEEP_RANK_MODEL_SPEC,
    max_results: int | None = None,
) -> DeepRankResult:
    """Run final ranking over coarse-kept candidates using structured model output."""
    client = model_client or FakeDeepRankModelClient()
    kept_candidates = [
        candidate
        for candidate in coarse_result.candidates
        if candidate.decision.keep
    ]
    ranked_candidates = [
        _deep_rank_candidate(
            candidate,
            coarse_result.normalized_query,
            client,
            model_spec,
        )
        for candidate in kept_candidates
    ]
    ranked_candidates = sorted(
        ranked_candidates,
        key=lambda item: (
            -item.decision.final_score,
            -item.candidate.decision.coarse_score,
            item.candidate.candidate.company.symbol,
        ),
    )
    ranked_candidates = _assign_ranks(ranked_candidates)
    if max_results is not None:
        ranked_candidates = ranked_candidates[:max_results]

    pipeline = PipelineStageTrace(
        stage="deep_rank",
        input_count=len(kept_candidates),
        output_count=len(ranked_candidates),
        notes=[
            f"normalized_query={coarse_result.normalized_query}",
            f"model_spec={model_spec.provider_name}:{model_spec.model_name}",
            "filtered coarse-rank candidates were excluded before deep ranking",
        ],
    )
    return DeepRankResult(
        normalized_query=coarse_result.normalized_query,
        model_spec=model_spec,
        candidates=ranked_candidates,
        pipeline=pipeline,
        data_boundary=list(coarse_result.data_boundary),
        warnings=list(coarse_result.warnings),
    )


def _deep_rank_candidate(
    candidate: CoarseRankedCandidate,
    normalized_query: str,
    model_client: ModelClient,
    model_spec: ModelSpec,
) -> DeepRankedCandidate:
    payload = _candidate_payload(candidate, normalized_query)
    raw_output = model_client.generate_structured(
        model_spec=model_spec,
        schema_name=DEEP_RANK_SCHEMA_NAME,
        payload=payload,
    )
    decision = _validate_model_decision(raw_output, candidate)
    return DeepRankedCandidate(candidate=candidate, decision=decision)


def _candidate_payload(
    candidate: CoarseRankedCandidate,
    normalized_query: str,
) -> dict[str, object]:
    enriched = candidate.candidate
    evidence = enriched.evidence_package.evidence
    return {
        "theme": normalized_query,
        "symbol": enriched.company.symbol,
        "name": enriched.company.name,
        "industry": enriched.company.industry,
        "concepts": list(enriched.company.concepts),
        "recall_score": enriched.recall_score,
        "coarse_score": candidate.decision.coarse_score,
        "coarse_reason": candidate.decision.reason,
        "coarse_risk_summary": candidate.decision.risk_summary,
        "evidence_ids": [item.id for item in evidence],
        "evidence_summaries": [_compressed_summary(item) for item in evidence],
        "missing_kinds": list(enriched.evidence_package.missing_kinds),
        "data_boundary": list(enriched.evidence_package.data_boundary),
    }


def _validate_model_decision(
    raw_output: Mapping[str, object],
    candidate: CoarseRankedCandidate,
) -> DeepRankDecision:
    try:
        decision = DeepRankDecision.model_validate(raw_output)
    except ValidationError as exc:
        raise ModelOutputValidationError("deep rank model output schema invalid") from exc

    symbol = candidate.candidate.company.symbol
    if decision.symbol != symbol:
        raise ModelOutputValidationError(
            f"deep rank symbol mismatch: {decision.symbol} != {symbol}"
        )
    evidence_ids = {item.id for item in candidate.candidate.evidence_package.evidence}
    unknown_ids = [
        evidence_id
        for evidence_id in decision.supporting_evidence_ids
        if evidence_id not in evidence_ids
    ]
    if unknown_ids:
        raise ModelOutputValidationError(
            f"deep rank referenced unknown evidence ids: {', '.join(unknown_ids)}"
        )
    _reject_trading_directives(decision)
    return decision


def _assign_ranks(candidates: list[DeepRankedCandidate]) -> list[DeepRankedCandidate]:
    ranked: list[DeepRankedCandidate] = []
    for index, candidate in enumerate(candidates, start=1):
        ranked.append(
            candidate.model_copy(
                update={"decision": candidate.decision.model_copy(update={"rank": index})}
            )
        )
    return ranked


def _reject_trading_directives(decision: DeepRankDecision) -> None:
    checked_text = " ".join(
        [
            decision.final_reason,
            decision.risk_assessment,
            decision.uncertainty,
            *decision.key_risks,
        ]
    ).casefold()
    for term in TRADING_DIRECTIVE_TERMS:
        if term.casefold() in checked_text:
            raise ModelSafetyError(
                f"deep rank model output contains trading directive: {term}"
            )


def _compressed_summary(item: EvidenceItem) -> str:
    return f"{item.id}|{item.kind}|{item.stance}|{item.summary}"


def _payload_list(payload: Mapping[str, object], key: str) -> list[str]:
    value = payload.get(key)
    if not isinstance(value, Sequence) or isinstance(value, str):
        return []
    return [str(item) for item in value]


def _clean_risk_summary(summary: str) -> str:
    parts = summary.split("|", maxsplit=3)
    return parts[-1] if parts else summary

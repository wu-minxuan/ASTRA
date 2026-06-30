"""Coarse ranking baseline for Phase 1 theme research."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Protocol

from pydantic import ValidationError

from astra.theme_research.contracts import (
    CoarseRankDecision,
    CoarseRankedCandidate,
    CoarseRankResult,
    EnrichedCandidate,
    EvidenceEnrichmentResult,
    EvidenceItem,
    ModelSpec,
    PipelineStageTrace,
)

COARSE_RANK_MODEL_SPEC = ModelSpec(
    provider_name="fake",
    model_name="fake-coarse-ranker-v1",
    purpose="coarse_rank",
    prompt_version="p1-t08-coarse-rank-v1",
    temperature=0.0,
    max_output_tokens=1024,
)
COARSE_RANK_SCHEMA_NAME = "phase1.coarse_rank.v1"
DEFAULT_MIN_KEEP_SCORE = 60.0
TRADING_DIRECTIVE_TERMS = (
    "买入",
    "卖出",
    "持仓",
    "建仓",
    "加仓",
    "减仓",
    "目标价",
    "仓位",
    "止盈",
    "止损",
    "buy",
    "sell",
    "hold",
    "target price",
)


class ModelOutputValidationError(RuntimeError):
    """Raised when structured model output cannot be accepted."""


class ModelSafetyError(RuntimeError):
    """Raised when model output violates research safety boundaries."""


class ModelClient(Protocol):
    """Minimal structured-output model client interface."""

    def generate_structured(
        self,
        *,
        model_spec: ModelSpec,
        schema_name: str,
        payload: Mapping[str, object],
    ) -> Mapping[str, object]:
        """Generate a structured model response for one payload."""


class FakeCoarseRankModelClient:
    """Deterministic fake model client for tests and local development."""

    def generate_structured(
        self,
        *,
        model_spec: ModelSpec,
        schema_name: str,
        payload: Mapping[str, object],
    ) -> Mapping[str, object]:
        if model_spec.purpose != "coarse_rank":
            raise ModelOutputValidationError("fake coarse ranker received wrong model purpose")
        if schema_name != COARSE_RANK_SCHEMA_NAME:
            raise ModelOutputValidationError("fake coarse ranker received wrong schema")

        symbol = str(payload["symbol"])
        recall_score = float(payload["recall_score"])
        evidence_ids = _payload_list(payload, "evidence_ids")
        evidence_text = " ".join(_payload_list(payload, "evidence_summaries"))
        missing_kinds = _payload_list(payload, "missing_kinds")
        weak_related = "弱相关" in evidence_text or "间接" in evidence_text

        score = recall_score + 10
        if missing_kinds:
            score -= min(30, len(missing_kinds) * 5)
        if weak_related:
            score = min(score, 45)
        score = max(0, min(100, score))
        keep = score >= DEFAULT_MIN_KEEP_SCORE and not weak_related
        evidence_refs = evidence_ids[:3] or evidence_ids
        reason_prefix = "保留" if keep else "过滤"
        return {
            "symbol": symbol,
            "coarse_score": score,
            "keep": keep,
            "reason": (
                f"粗排{reason_prefix}：结合召回分、主题证据和缺失证据边界，"
                f"该候选的主题相关性为{'较强' if keep else '较弱'}。"
            ),
            "risk_summary": "主要风险来自证据缺失、主题相关性或商业化不确定性。",
            "supporting_evidence_ids": evidence_refs,
        }


def coarse_rank_candidates(
    enrichment_result: EvidenceEnrichmentResult,
    model_client: ModelClient | None = None,
    model_spec: ModelSpec = COARSE_RANK_MODEL_SPEC,
    min_keep_score: float = DEFAULT_MIN_KEEP_SCORE,
) -> CoarseRankResult:
    """Run coarse ranking over enriched candidates using structured model output."""
    client = model_client or FakeCoarseRankModelClient()
    ranked_candidates = [
        _coarse_rank_candidate(
            candidate,
            enrichment_result.normalized_query,
            client,
            model_spec,
            min_keep_score,
        )
        for candidate in enrichment_result.candidates
    ]
    ranked_candidates = sorted(
        ranked_candidates,
        key=lambda item: (
            not item.decision.keep,
            -item.decision.coarse_score,
            item.candidate.company.symbol,
        ),
    )
    kept_count = sum(1 for item in ranked_candidates if item.decision.keep)
    pipeline = PipelineStageTrace(
        stage="coarse_rank",
        input_count=len(enrichment_result.candidates),
        output_count=kept_count,
        notes=[
            f"normalized_query={enrichment_result.normalized_query}",
            f"model_spec={model_spec.provider_name}:{model_spec.model_name}",
            f"min_keep_score={min_keep_score}",
        ],
    )
    return CoarseRankResult(
        normalized_query=enrichment_result.normalized_query,
        model_spec=model_spec,
        candidates=ranked_candidates,
        pipeline=pipeline,
        data_boundary=list(enrichment_result.data_boundary),
        warnings=list(enrichment_result.warnings),
    )


def _coarse_rank_candidate(
    candidate: EnrichedCandidate,
    normalized_query: str,
    model_client: ModelClient,
    model_spec: ModelSpec,
    min_keep_score: float,
) -> CoarseRankedCandidate:
    payload = _candidate_payload(candidate, normalized_query)
    raw_output = model_client.generate_structured(
        model_spec=model_spec,
        schema_name=COARSE_RANK_SCHEMA_NAME,
        payload=payload,
    )
    decision = _validate_model_decision(raw_output, candidate)
    decision = _apply_filtering_rules(decision, min_keep_score)
    return CoarseRankedCandidate(candidate=candidate, decision=decision)


def _candidate_payload(
    candidate: EnrichedCandidate,
    normalized_query: str,
) -> dict[str, object]:
    evidence = candidate.evidence_package.evidence
    return {
        "theme": normalized_query,
        "symbol": candidate.company.symbol,
        "name": candidate.company.name,
        "industry": candidate.company.industry,
        "concepts": list(candidate.company.concepts),
        "recall_score": candidate.recall_score,
        "recall_sources": [match.source for match in candidate.matches],
        "recall_signal_ids": [signal.id for signal in candidate.signals],
        "recall_signal_summary": (
            candidate.recall_assessment.recall_summary
            if candidate.recall_assessment is not None
            else None
        ),
        "recall_signal_evidence_gaps": (
            list(candidate.recall_assessment.evidence_gaps_to_fill)
            if candidate.recall_assessment is not None
            else []
        ),
        "evidence_ids": [item.id for item in evidence],
        "evidence_kinds": [item.kind for item in evidence],
        "evidence_summaries": [_compressed_summary(item) for item in evidence],
        "missing_kinds": list(candidate.evidence_package.missing_kinds),
        "data_boundary": list(candidate.evidence_package.data_boundary),
    }


def _validate_model_decision(
    raw_output: Mapping[str, object],
    candidate: EnrichedCandidate,
) -> CoarseRankDecision:
    try:
        decision = CoarseRankDecision.model_validate(raw_output)
    except ValidationError as exc:
        raise ModelOutputValidationError("coarse rank model output schema invalid") from exc

    if decision.symbol != candidate.company.symbol:
        raise ModelOutputValidationError(
            f"coarse rank symbol mismatch: {decision.symbol} != {candidate.company.symbol}"
        )
    evidence_ids = {item.id for item in candidate.evidence_package.evidence}
    unknown_ids = [
        evidence_id
        for evidence_id in decision.supporting_evidence_ids
        if evidence_id not in evidence_ids
    ]
    if unknown_ids:
        raise ModelOutputValidationError(
            f"coarse rank referenced unknown evidence ids: {', '.join(unknown_ids)}"
        )
    _reject_trading_directives(decision)
    return decision


def _apply_filtering_rules(
    decision: CoarseRankDecision,
    min_keep_score: float,
) -> CoarseRankDecision:
    if decision.keep and decision.coarse_score < min_keep_score:
        return decision.model_copy(
            update={
                "keep": False,
                "reason": (
                    f"{decision.reason} 粗排分 {decision.coarse_score:.1f} "
                    f"低于保留阈值 {min_keep_score:.1f}，因此过滤。"
                ),
            }
        )
    return decision


def _reject_trading_directives(decision: CoarseRankDecision) -> None:
    checked_text = " ".join(
        [
            decision.reason,
            decision.risk_summary,
        ]
    ).casefold()
    for term in TRADING_DIRECTIVE_TERMS:
        if term.casefold() in checked_text:
            raise ModelSafetyError(
                f"coarse rank model output contains trading directive: {term}"
            )


def _compressed_summary(item: EvidenceItem) -> str:
    return f"{item.id}|{item.kind}|{item.stance}|{item.summary}"


def _payload_list(payload: Mapping[str, object], key: str) -> list[str]:
    value = payload.get(key)
    if not isinstance(value, Sequence) or isinstance(value, str):
        return []
    return [str(item) for item in value]

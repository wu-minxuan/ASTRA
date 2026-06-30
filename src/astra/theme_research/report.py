"""Research report generation baseline for Phase 1 theme research."""

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
    CandidateStock,
    DeepRankedCandidate,
    DeepRankResult,
    FocusCompany,
    ModelSpec,
    PipelineStageTrace,
    ResearchReport,
    ScoreBreakdown,
    ScoreFactor,
    ThemeResearchResult,
)

REPORT_GENERATION_MODEL_SPEC = ModelSpec(
    provider_name="fake",
    model_name="fake-report-generator-v1",
    purpose="report_generation",
    prompt_version="p1-t10-report-generation-v1",
    temperature=0.0,
    max_output_tokens=2048,
)
REPORT_GENERATION_SCHEMA_NAME = "phase1.research_report.v1"
NOT_INVESTMENT_ADVICE = (
    "本报告仅用于研究流程验证和信息整理，不构成任何交易建议、收益承诺或操作依据。"
)


class FakeReportGenerationModelClient:
    """Deterministic fake report generator for tests and local development."""

    def generate_structured(
        self,
        *,
        model_spec: ModelSpec,
        schema_name: str,
        payload: Mapping[str, object],
    ) -> Mapping[str, object]:
        if model_spec.purpose != "report_generation":
            raise ModelOutputValidationError("fake report generator received wrong model purpose")
        if schema_name != REPORT_GENERATION_SCHEMA_NAME:
            raise ModelOutputValidationError("fake report generator received wrong schema")

        theme = str(payload["theme"])
        pool = _payload_list(payload, "pool")
        focus_companies = _payload_list(payload, "focus_companies")
        risks = _payload_list(payload, "risks")
        data_boundary = _payload_list(payload, "data_boundary")
        return {
            "title": f"{theme}主题股票池研究报告",
            "summary": f"基于 {len(pool)} 个候选的召回、证据补全和模型排序结果生成。",
            "theme_overview": f"{theme}主题关系来自结构化候选召回和证据包，不代表实时市场结论。",
            "pool_summary": "股票池按精排分数和稳定排序规则生成，后续仍需人工复核。",
            "focus_companies": focus_companies,
            "risks": risks or ["证据覆盖、数据时点和模型判断均存在不确定性。"],
            "data_boundary": "；".join(data_boundary)
            if data_boundary
            else "数据边界未提供。",
            "not_investment_advice": NOT_INVESTMENT_ADVICE,
        }


def generate_theme_research_result(
    deep_result: DeepRankResult,
    *,
    as_of: str,
    model_client: ModelClient | None = None,
    model_spec: ModelSpec = REPORT_GENERATION_MODEL_SPEC,
    max_focus_companies: int = 3,
) -> ThemeResearchResult:
    """Generate a structured Phase 1 research result from deep-ranked candidates."""
    pool = [candidate_stock_from_deep_ranked(candidate) for candidate in deep_result.candidates]
    client = model_client or FakeReportGenerationModelClient()
    payload = _report_payload(deep_result, pool, max_focus_companies)
    raw_report = client.generate_structured(
        model_spec=model_spec,
        schema_name=REPORT_GENERATION_SCHEMA_NAME,
        payload=payload,
    )
    report = _validate_report(raw_report, pool)
    pipeline = [
        deep_result.pipeline,
        PipelineStageTrace(
            stage="report_generation",
            input_count=len(pool),
            output_count=1 if report else 0,
            notes=[
                f"model_spec={model_spec.provider_name}:{model_spec.model_name}",
                "report generated from deep-rank result and structured evidence only",
            ],
        ),
    ]
    return ThemeResearchResult(
        as_of=as_of,
        pool=pool,
        report=report,
        pipeline=pipeline,
        data_boundary=list(deep_result.data_boundary),
        warnings=list(deep_result.warnings),
    )


def candidate_stock_from_deep_ranked(candidate: DeepRankedCandidate) -> CandidateStock:
    """Map one deep-ranked candidate into the public stock-pool contract."""
    enriched = candidate.candidate.candidate
    decision = candidate.decision
    company = enriched.company
    return CandidateStock(
        symbol=company.symbol,
        name=company.name,
        exchange=company.exchange,
        industry=company.industry or "未知行业",
        concepts=list(company.concepts) or ["未提供概念"],
        recall_sources=[match.reason for match in enriched.matches],
        evidence=list(enriched.evidence_package.evidence),
        scores=ScoreBreakdown(
            recall_score=enriched.recall_score,
            coarse_score=candidate.candidate.decision.coarse_score,
            final_score=decision.final_score,
            factors=[
                ScoreFactor(
                    name="recall_score",
                    value=enriched.recall_score,
                    reason="候选召回阶段的主题相关性分。",
                ),
                ScoreFactor(
                    name="coarse_score",
                    value=candidate.candidate.decision.coarse_score,
                    reason="模型粗排阶段的初筛分。",
                ),
                ScoreFactor(
                    name="final_score",
                    value=decision.final_score,
                    reason="模型精排阶段的最终排序分。",
                ),
            ],
        ),
        rank=decision.rank,
        selection_reason=decision.final_reason,
        key_risks=list(decision.key_risks),
    )


def _report_payload(
    deep_result: DeepRankResult,
    pool: list[CandidateStock],
    max_focus_companies: int,
) -> dict[str, object]:
    focus_companies = [
        FocusCompany(
            symbol=candidate.symbol,
            name=candidate.name,
            reason=candidate.selection_reason,
            supporting_evidence_ids=_supporting_ids_for_symbol(deep_result, candidate.symbol),
            risks=candidate.key_risks,
        ).model_dump()
        for candidate in pool[:max_focus_companies]
    ]
    risks = _deduplicate_strings(
        risk
        for candidate in pool
        for risk in candidate.key_risks
    )
    return {
        "theme": deep_result.normalized_query,
        "pool": [
            {
                "symbol": candidate.symbol,
                "name": candidate.name,
                "rank": candidate.rank,
                "final_score": candidate.scores.final_score,
                "selection_reason": candidate.selection_reason,
            }
            for candidate in pool
        ],
        "focus_companies": focus_companies,
        "risks": risks,
        "data_boundary": list(deep_result.data_boundary),
        "warnings": list(deep_result.warnings),
    }


def _validate_report(
    raw_report: Mapping[str, object],
    pool: list[CandidateStock],
) -> ResearchReport:
    try:
        report = ResearchReport.model_validate(raw_report)
    except ValidationError as exc:
        raise ModelOutputValidationError("report generation output schema invalid") from exc

    pool_symbols = {candidate.symbol for candidate in pool}
    for focus in report.focus_companies:
        if focus.symbol not in pool_symbols:
            raise ModelOutputValidationError(
                f"report referenced unknown focus company: {focus.symbol}"
            )
        evidence_ids = {
            evidence.id
            for candidate in pool
            if candidate.symbol == focus.symbol
            for evidence in candidate.evidence
        }
        unknown_ids = [
            evidence_id
            for evidence_id in focus.supporting_evidence_ids
            if evidence_id not in evidence_ids
        ]
        if unknown_ids:
            raise ModelOutputValidationError(
                f"report referenced unknown evidence ids: {', '.join(unknown_ids)}"
            )
    _reject_trading_directives(report)
    return report


def _reject_trading_directives(report: ResearchReport) -> None:
    checked_text = " ".join(
        [
            report.title,
            report.summary,
            report.theme_overview,
            report.pool_summary,
            *(focus.reason for focus in report.focus_companies),
            *report.risks,
        ]
    ).casefold()
    for term in TRADING_DIRECTIVE_TERMS:
        if term.casefold() in checked_text:
            raise ModelSafetyError(
                f"report generation output contains trading directive: {term}"
            )


def _supporting_ids_for_symbol(
    deep_result: DeepRankResult,
    symbol: str,
) -> list[str]:
    for candidate in deep_result.candidates:
        if candidate.candidate.candidate.company.symbol == symbol:
            return list(candidate.decision.supporting_evidence_ids)
    return []


def _payload_list(payload: Mapping[str, object], key: str) -> list[object]:
    value = payload.get(key)
    if not isinstance(value, Sequence) or isinstance(value, str):
        return []
    return list(value)


def _deduplicate_strings(values: Sequence[str]) -> list[str]:
    deduplicated: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value and value not in seen:
            deduplicated.append(value)
            seen.add(value)
    return deduplicated

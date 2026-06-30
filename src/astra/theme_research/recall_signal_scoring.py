"""Model-backed scoring for Phase 1 recall signals."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from collections.abc import Mapping
from pathlib import Path
from typing import Protocol

from pydantic import ValidationError

from astra.theme_research.coarse_rank import (
    TRADING_DIRECTIVE_TERMS,
    ModelOutputValidationError,
    ModelSafetyError,
)
from astra.theme_research.contracts import (
    CandidateRecallAssessment,
    CandidateRecallResult,
    ModelSpec,
    PipelineStageTrace,
    RecalledCandidate,
    RecallSignal,
    RecallSignalAssessment,
)

RECALL_SIGNAL_SCHEMA_NAME = "phase1.recall_signal_assessment.v1"
FAKE_RECALL_SIGNAL_MODEL_SPEC = ModelSpec(
    provider_name="fake",
    model_name="fake-recall-signal-scorer-v1",
    purpose="recall_signal_scoring",
    prompt_version="p1-o04-recall-signal-v1",
    temperature=0.0,
    max_output_tokens=1024,
)
DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEFAULT_DEEPSEEK_MODEL = "deepseek-v4-flash"
DEFAULT_DEEPSEEK_TIMEOUT_SECONDS = 30
DEFAULT_DEEPSEEK_MAX_OUTPUT_TOKENS = 4096
DEFAULT_DEEPSEEK_JSON_RETRIES = 2


class RecallSignalScoringError(RuntimeError):
    """Raised when recall signal scoring cannot produce accepted output."""


class RecallSignalScoringConfigurationError(RecallSignalScoringError):
    """Raised when a real recall signal scorer is missing configuration."""


class RecallSignalScorer(Protocol):
    """Scores structured recall signals into a numeric recall assessment."""

    model_spec: ModelSpec

    def score_candidate(
        self,
        *,
        normalized_query: str,
        candidate: RecalledCandidate,
    ) -> CandidateRecallAssessment:
        """Score one recalled candidate."""


class FakeRecallSignalScorer:
    """Deterministic scorer for non-live tests and local fallback injection."""

    model_spec = FAKE_RECALL_SIGNAL_MODEL_SPEC

    def score_candidate(
        self,
        *,
        normalized_query: str,
        candidate: RecalledCandidate,
    ) -> CandidateRecallAssessment:
        """Score one candidate using transparent local rules."""
        _require_signals(candidate)
        assessments = [_fake_signal_assessment(signal) for signal in candidate.signals]
        score = min(
            100.0,
            max(item.theme_relevance_score for item in assessments)
            + max(0, len(assessments) - 1) * 6,
        )
        strongest = [
            item.signal_id
            for item in sorted(
                assessments,
                key=lambda item: (-item.theme_relevance_score, item.signal_id),
            )[:2]
        ]
        gaps = _fake_evidence_gaps(candidate.signals)
        return CandidateRecallAssessment(
            symbol=candidate.company.symbol,
            recall_priority_score=score,
            strongest_signal_ids=strongest,
            recall_summary=(
                f"候选 {candidate.company.name} 由 {normalized_query} 的结构化召回信号支持；"
                "该分数来自 fake scorer，仅用于稳定自动化测试。"
            ),
            evidence_gaps_to_fill=gaps,
            signal_assessments=assessments,
        )


class DeepSeekRecallSignalScorer:
    """Real DeepSeek scorer using OpenAI-compatible chat completions."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = DEFAULT_DEEPSEEK_BASE_URL,
        model_name: str = DEFAULT_DEEPSEEK_MODEL,
        timeout_seconds: int = DEFAULT_DEEPSEEK_TIMEOUT_SECONDS,
    ) -> None:
        if not api_key:
            raise RecallSignalScoringConfigurationError("DEEPSEEK_API_KEY is not configured")
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self.model_spec = ModelSpec(
            provider_name="deepseek",
            model_name=model_name,
            purpose="recall_signal_scoring",
            prompt_version="p1-o04-recall-signal-v1",
            temperature=0.0,
            max_output_tokens=DEFAULT_DEEPSEEK_MAX_OUTPUT_TOKENS,
        )

    @classmethod
    def from_env(
        cls,
        *,
        env: Mapping[str, str] | None = None,
        dotenv_path: Path | None = None,
    ) -> DeepSeekRecallSignalScorer:
        """Create a scorer from environment variables or local .env."""
        source = env or os.environ
        dotenv_values = _read_dotenv(dotenv_path or _project_dotenv_path())
        api_key = source.get("DEEPSEEK_API_KEY") or dotenv_values.get("DEEPSEEK_API_KEY")
        base_url = (
            source.get("DEEPSEEK_BASE_URL")
            or dotenv_values.get("DEEPSEEK_BASE_URL")
            or DEFAULT_DEEPSEEK_BASE_URL
        )
        model_name = (
            source.get("DEEPSEEK_MODEL")
            or dotenv_values.get("DEEPSEEK_MODEL")
            or DEFAULT_DEEPSEEK_MODEL
        )
        return cls(api_key=api_key or "", base_url=base_url, model_name=model_name)

    def score_candidate(
        self,
        *,
        normalized_query: str,
        candidate: RecalledCandidate,
    ) -> CandidateRecallAssessment:
        """Score one candidate with DeepSeek and validate structured output."""
        _require_signals(candidate)
        payload = _candidate_payload(normalized_query, candidate)
        last_error: RecallSignalScoringError | None = None
        for attempt in range(DEFAULT_DEEPSEEK_JSON_RETRIES):
            request_body = {
                "model": self.model_spec.model_name,
                "messages": _messages_for_payload(payload, retry=attempt > 0),
                "temperature": self.model_spec.temperature,
                "max_tokens": self.model_spec.max_output_tokens,
                "response_format": {"type": "json_object"},
            }
            response = self._post_json("/chat/completions", request_body)
            content = _chat_completion_content(response)
            try:
                raw_output = _parse_json_object(content)
            except RecallSignalScoringError as exc:
                last_error = exc
                continue
            return _validate_assessment(raw_output, candidate)
        raise RecallSignalScoringError(
            "DeepSeek model content was invalid JSON after retry"
        ) from last_error

    def _post_json(
        self,
        path: str,
        payload: Mapping[str, object],
    ) -> Mapping[str, object]:
        url = f"{self._base_url}{path}"
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout_seconds) as response:
                raw_body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            safe_body = error_body.replace(self._api_key, "[redacted]")
            raise RecallSignalScoringError(
                f"DeepSeek API HTTP {exc.code}: {safe_body[:500]}"
            ) from exc
        except urllib.error.URLError as exc:
            raise RecallSignalScoringError(f"DeepSeek API unavailable: {exc.reason}") from exc
        except TimeoutError as exc:
            raise RecallSignalScoringError("DeepSeek API request timed out") from exc

        try:
            decoded = json.loads(raw_body)
        except json.JSONDecodeError as exc:
            raise RecallSignalScoringError("DeepSeek API returned invalid JSON") from exc
        if not isinstance(decoded, Mapping):
            raise RecallSignalScoringError("DeepSeek API response was not a JSON object")
        return decoded


def score_recall_signals(
    recall_result: CandidateRecallResult,
    *,
    scorer: RecallSignalScorer,
) -> CandidateRecallResult:
    """Attach model recall assessments and sort candidates by model score."""
    scored_candidates: list[RecalledCandidate] = []
    for candidate in recall_result.candidates:
        assessment = scorer.score_candidate(
            normalized_query=recall_result.normalized_query,
            candidate=candidate,
        )
        scored_candidates.append(
            candidate.model_copy(
                update={
                    "recall_assessment": assessment,
                    "recall_score": assessment.recall_priority_score,
                }
            )
        )

    scored_candidates = sorted(
        scored_candidates,
        key=lambda candidate: (
            -candidate.recall_score,
            candidate.company.symbol,
        ),
    )
    pipeline = PipelineStageTrace(
        stage=recall_result.pipeline.stage,
        input_count=recall_result.pipeline.input_count,
        output_count=len(scored_candidates),
        notes=[
            *recall_result.pipeline.notes,
            (
                "recall_signal_model_spec="
                f"{scorer.model_spec.provider_name}:{scorer.model_spec.model_name}"
            ),
            "recall_score mirrors recall_priority_score after P1-O04 signal scoring",
        ],
    )
    return recall_result.model_copy(
        update={
            "candidates": scored_candidates,
            "pipeline": pipeline,
            "recall_signal_model_spec": scorer.model_spec,
        }
    )


def _fake_signal_assessment(signal: RecallSignal) -> RecallSignalAssessment:
    if signal.signal_type == "provider_concept_board":
        score = 88.0 if not signal.is_fallback else 76.0
        directness = "direct"
    elif signal.signal_type == "fixture_concept":
        score = 72.0
        directness = "direct"
    elif signal.signal_type == "fixture_keyword":
        score = 64.0
        directness = "adjacent"
    else:
        score = 42.0
        directness = "weak"
    if signal.confidence == "low":
        score -= 10
    return RecallSignalAssessment(
        signal_id=signal.id,
        theme_relevance_score=max(0.0, min(100.0, score)),
        directness=directness,
        source_confidence=signal.confidence,
        rationale=f"fake scorer 根据 {signal.signal_type} 和来源置信度给出可复现评分。",
    )


def _fake_evidence_gaps(signals: list[RecallSignal]) -> list[str]:
    gaps: list[str] = []
    if any(signal.is_fallback for signal in signals):
        gaps.append("需要刷新真实市场数据源以确认缓存召回关系。")
    if not any(signal.source_type == "market_data_provider" for signal in signals):
        gaps.append("需要真实市场数据源或公开资料交叉验证召回关系。")
    return gaps


def _candidate_payload(
    normalized_query: str,
    candidate: RecalledCandidate,
) -> dict[str, object]:
    return {
        "schema_name": RECALL_SIGNAL_SCHEMA_NAME,
        "task": "score recall signals for theme relevance, not investment merit",
        "theme": normalized_query,
        "candidate": {
            "symbol": candidate.company.symbol,
            "name": candidate.company.name,
            "industry": candidate.company.industry,
            "concepts": list(candidate.company.concepts),
            "legacy_recall_score": candidate.recall_score,
            "signals": [signal.model_dump(mode="json") for signal in candidate.signals],
        },
        "output_contract": {
            "symbol": candidate.company.symbol,
            "recall_priority_score": "number 0-100",
            "strongest_signal_ids": "non-empty list of provided signal ids",
            "recall_summary": "Chinese explanation under 80 chars, no trading recommendation",
            "evidence_gaps_to_fill": "0-3 concise evidence gaps for later enrichment",
            "signal_assessments": [
                {
                    "signal_id": "provided signal id",
                    "theme_relevance_score": "number 0-100",
                    "directness": "direct|adjacent|weak",
                    "source_confidence": "low|medium|high",
                    "rationale": "Chinese rationale under 50 chars, no trading recommendation",
                }
            ],
        },
    }


def _messages_for_payload(
    payload: Mapping[str, object],
    *,
    retry: bool,
) -> list[dict[str, str]]:
    messages = [
        {"role": "system", "content": _system_prompt()},
        {
            "role": "user",
            "content": json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        },
    ]
    if retry:
        messages.append(
            {
                "role": "user",
                "content": (
                    "The previous response was truncated or invalid. "
                    "Return compact valid JSON only, with no markdown, no comments, "
                    "no whitespace-heavy formatting, and all required fields."
                ),
            }
        )
    return messages


def _system_prompt() -> str:
    return (
        "You are ASTRA's recall-signal scorer. Score whether each recall signal "
        "explains why an A-share company belongs in a theme candidate pool. "
        "This is not stock recommendation or trading advice. Return only one compact "
        "valid JSON object matching the requested contract. Assess every provided signal. "
        "Use concise Chinese for rationale fields. Keep recall_summary under 80 "
        "Chinese characters, each rationale under 50 Chinese characters, and "
        "evidence_gaps_to_fill at most 3 short strings. Do not include buy, sell, "
        "hold, target price, position sizing, or any trading directive."
    )


def _validate_assessment(
    raw_output: Mapping[str, object],
    candidate: RecalledCandidate,
) -> CandidateRecallAssessment:
    try:
        assessment = CandidateRecallAssessment.model_validate(raw_output)
    except ValidationError as exc:
        raise ModelOutputValidationError("recall signal model output schema invalid") from exc

    if assessment.symbol != candidate.company.symbol:
        raise ModelOutputValidationError(
            "recall signal symbol mismatch: "
            f"{assessment.symbol} != {candidate.company.symbol}"
        )
    signal_ids = {signal.id for signal in candidate.signals}
    strongest_unknown = [
        signal_id
        for signal_id in assessment.strongest_signal_ids
        if signal_id not in signal_ids
    ]
    if strongest_unknown:
        raise ModelOutputValidationError(
            "recall signal assessment referenced unknown strongest signal ids: "
            f"{', '.join(strongest_unknown)}"
        )
    assessed_ids = {item.signal_id for item in assessment.signal_assessments}
    if assessed_ids != signal_ids:
        missing = sorted(signal_ids - assessed_ids)
        unknown = sorted(assessed_ids - signal_ids)
        raise ModelOutputValidationError(
            "recall signal assessment must cover every signal; "
            f"missing={','.join(missing)} unknown={','.join(unknown)}"
        )
    _reject_trading_directives(assessment)
    return assessment


def _reject_trading_directives(assessment: CandidateRecallAssessment) -> None:
    checked_text = " ".join(
        [
            assessment.recall_summary,
            *assessment.evidence_gaps_to_fill,
            *(item.rationale for item in assessment.signal_assessments),
        ]
    ).casefold()
    for term in TRADING_DIRECTIVE_TERMS:
        if term.casefold() in checked_text:
            raise ModelSafetyError(
                f"recall signal model output contains trading directive: {term}"
            )


def _require_signals(candidate: RecalledCandidate) -> None:
    if not candidate.signals:
        raise RecallSignalScoringError(
            f"candidate has no recall signals: {candidate.company.symbol}"
        )


def _chat_completion_content(response: Mapping[str, object]) -> str:
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        raise RecallSignalScoringError("DeepSeek API response missing choices")
    first_choice = choices[0]
    if not isinstance(first_choice, Mapping):
        raise RecallSignalScoringError("DeepSeek API choice was not an object")
    message = first_choice.get("message")
    if not isinstance(message, Mapping):
        raise RecallSignalScoringError("DeepSeek API choice missing message")
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise RecallSignalScoringError("DeepSeek API message content is empty")
    return content


def _parse_json_object(content: str) -> Mapping[str, object]:
    stripped = content.strip()
    if not stripped.startswith("{"):
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start < 0 or end < start:
            raise RecallSignalScoringError("DeepSeek model content did not contain JSON")
        stripped = stripped[start : end + 1]
    try:
        decoded = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise RecallSignalScoringError("DeepSeek model content was invalid JSON") from exc
    if not isinstance(decoded, Mapping):
        raise RecallSignalScoringError("DeepSeek model content was not a JSON object")
    return decoded


def _project_dotenv_path() -> Path:
    return Path(__file__).resolve().parents[3] / ".env"


def _read_dotenv(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", maxsplit=1)
        key = key.strip()
        value = value.strip().strip("\"'")
        if key:
            values[key] = value
    return values

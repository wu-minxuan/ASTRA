import json
from pathlib import Path
from typing import Any

import pytest

from astra.theme_research.coarse_rank import ModelOutputValidationError
from astra.theme_research.fixtures import load_low_altitude_economy_fixture
from astra.theme_research.recall import recall_candidates
from astra.theme_research.recall_signal_scoring import (
    DeepSeekRecallSignalScorer,
    FakeRecallSignalScorer,
    score_recall_signals,
)


class StubDeepSeekRecallSignalScorer(DeepSeekRecallSignalScorer):
    def __init__(self, content: str) -> None:
        super().__init__(api_key="unit-test-key", base_url="https://unit.test")
        self.content = content
        self.last_payload: dict[str, Any] | None = None

    def _post_json(self, path: str, payload: dict[str, object]) -> dict[str, object]:
        self.last_payload = {"path": path, "payload": payload}
        return {"choices": [{"message": {"content": self.content}}]}


def test_fake_recall_signal_scorer_attaches_assessments_and_sorts() -> None:
    dataset = load_low_altitude_economy_fixture()
    recall_result = recall_candidates("低空经济", dataset, max_candidates=3)

    scored = score_recall_signals(
        recall_result,
        scorer=FakeRecallSignalScorer(),
    )

    assert scored.recall_signal_model_spec is not None
    assert scored.recall_signal_model_spec.provider_name == "fake"
    assert scored.candidates == sorted(
        scored.candidates,
        key=lambda candidate: (-candidate.recall_score, candidate.company.symbol),
    )
    assert all(candidate.recall_assessment is not None for candidate in scored.candidates)
    assert all(
        candidate.recall_score == candidate.recall_assessment.recall_priority_score
        for candidate in scored.candidates
        if candidate.recall_assessment is not None
    )
    assert any(
        "recall_signal_model_spec=fake:fake-recall-signal-scorer-v1" in note
        for note in scored.pipeline.notes
    )


def test_deepseek_recall_signal_scorer_validates_structured_content() -> None:
    dataset = load_low_altitude_economy_fixture()
    candidate = recall_candidates("低空经济", dataset, max_candidates=1).candidates[0]
    signal_ids = [signal.id for signal in candidate.signals]
    content = json.dumps(
        {
            "symbol": candidate.company.symbol,
            "recall_priority_score": 83,
            "strongest_signal_ids": signal_ids[:1],
            "recall_summary": "候选与主题存在直接召回关系。",
            "evidence_gaps_to_fill": ["需要后续证据补全验证基本面。"],
            "signal_assessments": [
                {
                    "signal_id": signal_id,
                    "theme_relevance_score": 80,
                    "directness": "direct",
                    "source_confidence": "medium",
                    "rationale": "信号能解释主题召回关系。",
                }
                for signal_id in signal_ids
            ],
        },
        ensure_ascii=False,
    )
    scorer = StubDeepSeekRecallSignalScorer(content)

    assessment = scorer.score_candidate(
        normalized_query="低空经济",
        candidate=candidate,
    )

    assert assessment.symbol == candidate.company.symbol
    assert assessment.recall_priority_score == 83
    assert scorer.model_spec.provider_name == "deepseek"
    assert scorer.last_payload is not None
    assert scorer.last_payload["path"] == "/chat/completions"


def test_deepseek_recall_signal_scorer_rejects_unknown_signal_ids() -> None:
    dataset = load_low_altitude_economy_fixture()
    candidate = recall_candidates("低空经济", dataset, max_candidates=1).candidates[0]
    content = json.dumps(
        {
            "symbol": candidate.company.symbol,
            "recall_priority_score": 83,
            "strongest_signal_ids": ["unknown-signal"],
            "recall_summary": "候选与主题存在直接召回关系。",
            "evidence_gaps_to_fill": [],
            "signal_assessments": [
                {
                    "signal_id": "unknown-signal",
                    "theme_relevance_score": 80,
                    "directness": "direct",
                    "source_confidence": "medium",
                    "rationale": "信号能解释主题召回关系。",
                }
            ],
        },
        ensure_ascii=False,
    )
    scorer = StubDeepSeekRecallSignalScorer(content)

    with pytest.raises(ModelOutputValidationError):
        scorer.score_candidate(normalized_query="低空经济", candidate=candidate)


def test_deepseek_recall_signal_scorer_can_read_local_dotenv(tmp_path: Path) -> None:
    dotenv = tmp_path / ".env"
    dotenv.write_text(
        "\n".join(
            [
                "DEEPSEEK_API_KEY=unit-test-key",
                "DEEPSEEK_BASE_URL=https://unit.test",
                "DEEPSEEK_MODEL=deepseek-v4-flash",
            ]
        ),
        encoding="utf-8",
    )

    scorer = DeepSeekRecallSignalScorer.from_env(env={}, dotenv_path=dotenv)

    assert scorer.model_spec.provider_name == "deepseek"
    assert scorer.model_spec.model_name == "deepseek-v4-flash"

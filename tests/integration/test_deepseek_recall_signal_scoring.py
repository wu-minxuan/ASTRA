import pytest

from astra.theme_research.fixtures import load_low_altitude_economy_fixture
from astra.theme_research.recall import recall_candidates
from astra.theme_research.recall_signal_scoring import (
    DeepSeekRecallSignalScorer,
    score_recall_signals,
)

pytestmark = pytest.mark.live


def test_live_deepseek_recall_signal_scorer_scores_fixture_candidate() -> None:
    dataset = load_low_altitude_economy_fixture()
    recall_result = recall_candidates("低空经济", dataset, max_candidates=1)

    scored = score_recall_signals(
        recall_result,
        scorer=DeepSeekRecallSignalScorer.from_env(),
    )

    candidate = scored.candidates[0]
    assessment = candidate.recall_assessment

    assert scored.recall_signal_model_spec is not None
    assert scored.recall_signal_model_spec.provider_name == "deepseek"
    assert assessment is not None
    assert assessment.symbol == candidate.company.symbol
    assert 0 <= assessment.recall_priority_score <= 100
    assert candidate.recall_score == assessment.recall_priority_score
    assert {item.signal_id for item in assessment.signal_assessments} == {
        signal.id for signal in candidate.signals
    }
    assert assessment.strongest_signal_ids

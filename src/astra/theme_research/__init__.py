"""Theme research domain models and fixtures."""

from astra.theme_research.contracts import (
    CONTRACT_VERSION,
    CandidateStock,
    EvidenceItem,
    FixtureCompany,
    FixtureThemeDataset,
    FocusCompany,
    NormalizedThemeRequest,
    PipelineStageTrace,
    ResearchReport,
    ScoreBreakdown,
    ScoreFactor,
    ThemeResearchError,
    ThemeResearchErrorResponse,
    ThemeResearchRequest,
    ThemeResearchResponse,
    ThemeResearchResult,
)
from astra.theme_research.fixtures import load_low_altitude_economy_fixture

__all__ = [
    "CONTRACT_VERSION",
    "CandidateStock",
    "EvidenceItem",
    "FixtureCompany",
    "FixtureThemeDataset",
    "FocusCompany",
    "NormalizedThemeRequest",
    "PipelineStageTrace",
    "ResearchReport",
    "ScoreBreakdown",
    "ScoreFactor",
    "ThemeResearchError",
    "ThemeResearchErrorResponse",
    "ThemeResearchRequest",
    "ThemeResearchResponse",
    "ThemeResearchResult",
    "load_low_altitude_economy_fixture",
]

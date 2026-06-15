"""Candidate recall for Phase 1 fixed theme research data."""

from typing import Optional

from astra.theme_research.contracts import (
    CandidateRecallResult,
    FixtureCompany,
    FixtureThemeDataset,
    PipelineStageTrace,
    RecalledCandidate,
    RecallMatch,
)


def normalize_theme_query(theme: str) -> str:
    """Normalize a user theme query for deterministic fixture matching."""
    return theme.strip().casefold()


def recall_candidates(
    theme: str,
    dataset: FixtureThemeDataset,
    max_candidates: Optional[int] = None,
) -> CandidateRecallResult:
    """Recall candidate companies from a fixed theme fixture dataset."""
    normalized_query = normalize_theme_query(theme)
    matched_aliases = _matched_aliases(normalized_query, dataset)
    candidates: list[RecalledCandidate] = []

    if normalized_query:
        query_terms = {normalized_query}
        if matched_aliases:
            query_terms.update(normalize_theme_query(alias) for alias in dataset.aliases)
            query_terms.add(normalize_theme_query(dataset.display_name))

        for company in dataset.companies:
            candidate = _recall_company(company, query_terms, matched_aliases)
            if candidate is not None:
                candidates.append(candidate)

    candidates = sorted(
        candidates,
        key=lambda candidate: (-candidate.recall_score, candidate.company.symbol),
    )
    if max_candidates is not None:
        candidates = candidates[:max_candidates]

    pipeline = PipelineStageTrace(
        stage="candidate_recall",
        input_count=len(dataset.companies),
        output_count=len(candidates),
        notes=_pipeline_notes(normalized_query, matched_aliases, max_candidates),
    )
    return CandidateRecallResult(
        normalized_query=normalized_query,
        matched_aliases=matched_aliases,
        candidates=candidates,
        pipeline=pipeline,
    )


def _matched_aliases(normalized_query: str, dataset: FixtureThemeDataset) -> list[str]:
    if not normalized_query:
        return []
    return [
        alias
        for alias in dataset.aliases
        if normalize_theme_query(alias) == normalized_query
    ]


def _recall_company(
    company: FixtureCompany,
    query_terms: set[str],
    matched_aliases: list[str],
) -> Optional[RecalledCandidate]:
    matches: list[RecallMatch] = []

    for concept in company.concepts:
        if normalize_theme_query(concept) in query_terms:
            matches.append(
                RecallMatch(
                    source="concept",
                    term=concept,
                    reason=f"公司概念命中主题词：{concept}",
                )
            )

    for keyword in company.recall_keywords:
        if normalize_theme_query(keyword) in query_terms:
            matches.append(
                RecallMatch(
                    source="recall_keyword",
                    term=keyword,
                    reason=f"召回关键词命中主题词：{keyword}",
                )
            )

    if matched_aliases and not matches:
        matches.append(
            RecallMatch(
                source="theme_alias",
                term=matched_aliases[0],
                reason="主题别名命中固定样例，召回阶段保留弱相关候选。",
            )
        )

    if not matches:
        return None

    return RecalledCandidate(
        company=company,
        matches=_deduplicate_matches(matches),
        recall_score=_score_matches(matches),
    )


def _deduplicate_matches(matches: list[RecallMatch]) -> list[RecallMatch]:
    deduplicated: list[RecallMatch] = []
    seen: set[tuple[str, str]] = set()
    for match in matches:
        key = (match.source, normalize_theme_query(match.term))
        if key not in seen:
            deduplicated.append(match)
            seen.add(key)
    return deduplicated


def _score_matches(matches: list[RecallMatch]) -> float:
    score = 0.0
    for match in _deduplicate_matches(matches):
        if match.source == "concept":
            score += 45
        elif match.source == "recall_keyword":
            score += 35
        elif match.source == "theme_alias":
            score += 10
    return min(score, 100.0)


def _pipeline_notes(
    normalized_query: str,
    matched_aliases: list[str],
    max_candidates: Optional[int],
) -> list[str]:
    notes = [f"normalized_query={normalized_query}"]
    if matched_aliases:
        notes.append("theme alias matched; fixture theme candidates were recalled")
    else:
        notes.append("no fixture theme alias matched; only direct company terms were used")
    if max_candidates is not None:
        notes.append(f"max_candidates={max_candidates}")
    return notes

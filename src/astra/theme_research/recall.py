"""Candidate recall for Phase 1 fixed theme research data."""

from typing import Optional

from astra.theme_research.contracts import (
    CandidateRecallResult,
    ConceptBoardRecord,
    ConceptConstituentRecord,
    FixtureCompany,
    FixtureThemeDataset,
    MarketDataCompany,
    PipelineStageTrace,
    ProviderMetadata,
    RecalledCandidate,
    RecallMatch,
    RecallSignal,
    RecallSignalConfidence,
    RecallSignalType,
)
from astra.theme_research.market_data import (
    MarketDataProvider,
    market_data_company_from_concept_record,
)

FIXTURE_RECALL_INTERFACE = "load_low_altitude_economy_fixture"


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
            candidate = _recall_fixture_company(
                company,
                query_terms,
                matched_aliases,
                dataset.as_of,
            )
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


def recall_candidates_from_provider(
    theme: str,
    provider: MarketDataProvider,
    fallback_dataset: Optional[FixtureThemeDataset] = None,
    max_candidates: Optional[int] = None,
) -> CandidateRecallResult:
    """Recall candidate companies from provider concept boards with fixture fallback."""
    normalized_query = normalize_theme_query(theme)
    matched_aliases = (
        _matched_aliases(normalized_query, fallback_dataset)
        if fallback_dataset is not None
        else []
    )
    query_terms = _concept_query_terms(theme, fallback_dataset, matched_aliases)
    warnings: list[str] = []
    notes = [f"normalized_query={normalized_query}"]

    boards = _list_concept_boards(provider, warnings)
    matched_boards = _match_concept_boards(boards, query_terms)
    concept_names = _concept_names_to_query(matched_boards, query_terms, boards, notes)
    boards_by_name = {normalize_theme_query(board.concept_name): board for board in boards}

    candidates_by_symbol: dict[str, RecalledCandidate] = {}
    for concept_name in concept_names:
        try:
            records = provider.list_concept_constituents(concept_name)
        except Exception as exc:
            warnings.append(f"concept constituents unavailable for {concept_name}: {exc}")
            continue
        if not records:
            warnings.append(f"concept constituents empty for {concept_name}")
            continue
        for record in records:
            _merge_provider_candidate(
                candidates_by_symbol,
                record,
                boards_by_name.get(normalize_theme_query(concept_name)),
            )

    candidates = sorted(
        candidates_by_symbol.values(),
        key=lambda candidate: (-candidate.recall_score, candidate.company.symbol),
    )
    if max_candidates is not None:
        candidates = candidates[:max_candidates]

    if not candidates and fallback_dataset is not None:
        fallback_result = recall_candidates(theme, fallback_dataset, max_candidates)
        fallback_pipeline = fallback_result.pipeline.model_copy(
            update={
                "notes": [
                    *fallback_result.pipeline.notes,
                    "market data provider returned no usable candidates; fixture fallback used",
                ]
            }
        )
        return fallback_result.model_copy(
            update={
                "pipeline": fallback_pipeline,
                "warnings": [
                    *warnings,
                    "fixture fallback used for candidate recall",
                ],
            }
        )

    pipeline = PipelineStageTrace(
        stage="candidate_recall",
        input_count=len(concept_names),
        output_count=len(candidates),
        notes=[
            *notes,
            f"concept_queries={','.join(concept_names)}",
        ],
    )
    return CandidateRecallResult(
        normalized_query=normalized_query,
        matched_aliases=matched_aliases,
        matched_concept_boards=[board.concept_name for board in matched_boards],
        candidates=candidates,
        pipeline=pipeline,
        warnings=warnings,
    )


def _matched_aliases(normalized_query: str, dataset: FixtureThemeDataset) -> list[str]:
    if not normalized_query:
        return []
    return [
        alias
        for alias in dataset.aliases
        if normalize_theme_query(alias) == normalized_query
    ]


def _recall_fixture_company(
    company: FixtureCompany,
    query_terms: set[str],
    matched_aliases: list[str],
    retrieved_at: str,
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
        company=_fixture_company_to_market_data_company(company, retrieved_at),
        matches=_deduplicate_matches(matches),
        signals=_signals_from_fixture_matches(company, matches, retrieved_at),
        recall_score=_score_matches(matches),
        fixture_company=company,
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
        elif match.source == "provider_concept_board":
            score += 70
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


def _fixture_company_to_market_data_company(
    company: FixtureCompany,
    retrieved_at: str,
) -> MarketDataCompany:
    return MarketDataCompany(
        symbol=company.symbol,
        name=company.name,
        exchange=company.exchange,
        industry=company.industry,
        concepts=list(company.concepts),
        provider=ProviderMetadata(
            provider_name="fixture",
            provider_interface=FIXTURE_RECALL_INTERFACE,
            retrieved_at=retrieved_at,
            is_fallback=True,
        ),
    )


def _concept_query_terms(
    theme: str,
    dataset: Optional[FixtureThemeDataset],
    matched_aliases: list[str],
) -> list[str]:
    terms = [theme.strip()]
    if dataset is not None and matched_aliases:
        terms.extend(dataset.aliases)
        terms.append(dataset.display_name)
    deduplicated: list[str] = []
    seen: set[str] = set()
    for term in terms:
        normalized_term = normalize_theme_query(term)
        if normalized_term and normalized_term not in seen:
            deduplicated.append(term.strip())
            seen.add(normalized_term)
    return deduplicated


def _list_concept_boards(
    provider: MarketDataProvider,
    warnings: list[str],
) -> list[ConceptBoardRecord]:
    try:
        return provider.list_concept_boards()
    except Exception as exc:
        warnings.append(f"concept board discovery unavailable: {exc}")
        return []


def _match_concept_boards(
    boards: list[ConceptBoardRecord],
    query_terms: list[str],
) -> list[ConceptBoardRecord]:
    matched: list[ConceptBoardRecord] = []
    seen: set[str] = set()
    normalized_terms = [normalize_theme_query(term) for term in query_terms]
    for board in boards:
        normalized_board = normalize_theme_query(board.concept_name)
        if not normalized_board:
            continue
        board_key = board.board_code or normalized_board
        for normalized_term in normalized_terms:
            if not normalized_term:
                continue
            if (
                normalized_board == normalized_term
                or normalized_term in normalized_board
                or normalized_board in normalized_term
            ):
                if board_key not in seen:
                    matched.append(board)
                    seen.add(board_key)
                break
    return matched


def _concept_names_to_query(
    matched_boards: list[ConceptBoardRecord],
    query_terms: list[str],
    boards: list[ConceptBoardRecord],
    notes: list[str],
) -> list[str]:
    if matched_boards:
        notes.append("concept board discovery matched provider names")
        return _deduplicate_terms([board.concept_name for board in matched_boards])
    if boards:
        notes.append("concept board discovery returned no name matches; direct terms used")
    else:
        notes.append("concept board discovery unavailable or empty; direct terms used")
    return _deduplicate_terms(query_terms)


def _deduplicate_terms(terms: list[str]) -> list[str]:
    deduplicated: list[str] = []
    seen: set[str] = set()
    for term in terms:
        normalized_term = normalize_theme_query(term)
        if normalized_term and normalized_term not in seen:
            deduplicated.append(term)
            seen.add(normalized_term)
    return deduplicated


def _merge_provider_candidate(
    candidates_by_symbol: dict[str, RecalledCandidate],
    record: ConceptConstituentRecord,
    board: ConceptBoardRecord | None = None,
) -> None:
    match = RecallMatch(
        source="provider_concept_board",
        term=record.concept_name,
        reason=f"真实概念板块成分命中：{record.concept_name}",
    )
    signal = _signal_from_provider_record(record, board)
    existing = candidates_by_symbol.get(record.symbol)
    if existing is None:
        candidates_by_symbol[record.symbol] = RecalledCandidate(
            company=market_data_company_from_concept_record(record),
            matches=[match],
            signals=[signal],
            recall_score=_score_matches([match]),
        )
        return

    matches = _deduplicate_matches([*existing.matches, match])
    signals = _deduplicate_signals([*existing.signals, signal])
    concepts = _deduplicate_terms([*existing.company.concepts, record.concept_name])
    company = existing.company.model_copy(update={"concepts": concepts})
    candidates_by_symbol[record.symbol] = existing.model_copy(
        update={
            "company": company,
            "matches": matches,
            "signals": signals,
            "recall_score": _score_matches(matches),
        }
    )


def _signals_from_fixture_matches(
    company: FixtureCompany,
    matches: list[RecallMatch],
    retrieved_at: str,
) -> list[RecallSignal]:
    signals: list[RecallSignal] = []
    for match in _deduplicate_matches(matches):
        signal_type = _fixture_signal_type(match)
        signals.append(
            RecallSignal(
                id=_signal_id(company.symbol, signal_type, match.term, FIXTURE_RECALL_INTERFACE),
                signal_type=signal_type,
                source_name="ASTRA Phase 1 fixture",
                source_type="fixture",
                provider_name="fixture",
                provider_interface=FIXTURE_RECALL_INTERFACE,
                matched_term=match.term,
                normalized_term=normalize_theme_query(match.term),
                reason=match.reason,
                confidence=_fixture_signal_confidence(match),
                concept_name=match.term if match.source == "concept" else None,
                symbol=company.symbol,
                is_fallback=True,
                retrieved_at=retrieved_at,
            )
        )
    return _deduplicate_signals(signals)


def _signal_from_provider_record(
    record: ConceptConstituentRecord,
    board: ConceptBoardRecord | None,
) -> RecallSignal:
    metadata = record.provider
    confidence = "medium" if metadata.is_fallback else "high"
    return RecallSignal(
        id=_signal_id(
            record.symbol,
            "provider_concept_board",
            record.concept_name,
            metadata.provider_interface,
        ),
        signal_type="provider_concept_board",
        source_name=f"{metadata.provider_name}:{metadata.provider_interface}",
        source_type="market_data_provider",
        provider_name=metadata.provider_name,
        provider_interface=metadata.provider_interface,
        matched_term=record.concept_name,
        normalized_term=normalize_theme_query(record.concept_name),
        reason=f"真实概念板块成分命中：{record.concept_name}",
        confidence=confidence,
        concept_name=record.concept_name,
        board_code=board.board_code if board is not None else None,
        symbol=record.symbol,
        is_fallback=metadata.is_fallback,
        failure_reason=metadata.failure_reason,
        retrieved_at=metadata.retrieved_at,
    )


def _fixture_signal_type(match: RecallMatch) -> RecallSignalType:
    if match.source == "concept":
        return "fixture_concept"
    if match.source == "recall_keyword":
        return "fixture_keyword"
    return "theme_alias"


def _fixture_signal_confidence(match: RecallMatch) -> RecallSignalConfidence:
    if match.source in {"concept", "recall_keyword"}:
        return "medium"
    return "low"


def _deduplicate_signals(signals: list[RecallSignal]) -> list[RecallSignal]:
    deduplicated: list[RecallSignal] = []
    seen: set[tuple[str, str, str, Optional[str]]] = set()
    for signal in signals:
        key = (
            signal.signal_type,
            signal.provider_interface,
            normalize_theme_query(signal.matched_term),
            signal.symbol,
        )
        if key not in seen:
            deduplicated.append(signal)
            seen.add(key)
    return deduplicated


def _signal_id(
    symbol: str,
    signal_type: str,
    matched_term: str,
    provider_interface: str,
) -> str:
    return (
        f"{symbol}:{signal_type}:"
        f"{provider_interface}:{normalize_theme_query(matched_term)}"
    )

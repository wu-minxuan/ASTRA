from astra.theme_research import load_low_altitude_economy_fixture
from astra.theme_research.recall import normalize_theme_query, recall_candidates


def test_normalize_theme_query_trims_and_casefolds() -> None:
    assert normalize_theme_query("  eVTOL  ") == "evtOL".casefold()


def test_recall_candidates_matches_fixture_theme_alias() -> None:
    dataset = load_low_altitude_economy_fixture()

    result = recall_candidates("低空经济", dataset)

    assert result.normalized_query == "低空经济"
    assert result.matched_aliases == ["低空经济"]
    assert len(result.candidates) == len(dataset.companies)
    assert result.pipeline.stage == "candidate_recall"
    assert result.pipeline.input_count == len(dataset.companies)
    assert result.pipeline.output_count == len(dataset.companies)
    assert result.candidates[0].company.symbol == "999001.SZ"


def test_recall_candidates_supports_alias_query() -> None:
    dataset = load_low_altitude_economy_fixture()

    result = recall_candidates("无人机", dataset)
    recalled_symbols = {candidate.company.symbol for candidate in result.candidates}

    assert result.matched_aliases == ["无人机"]
    assert "999002.SZ" in recalled_symbols
    assert len(result.candidates) == len(dataset.companies)


def test_recall_candidates_returns_empty_for_unknown_theme() -> None:
    dataset = load_low_altitude_economy_fixture()

    result = recall_candidates("不存在的主题", dataset)

    assert result.matched_aliases == []
    assert result.candidates == []
    assert result.pipeline.output_count == 0


def test_recall_candidates_deduplicates_multi_source_matches() -> None:
    dataset = load_low_altitude_economy_fixture()

    result = recall_candidates("低空经济", dataset)
    symbols = [candidate.company.symbol for candidate in result.candidates]
    first_candidate = result.candidates[0]
    first_sources = {match.source for match in first_candidate.matches}

    assert len(symbols) == len(set(symbols))
    assert first_candidate.company.symbol == "999001.SZ"
    assert {"concept", "recall_keyword"}.issubset(first_sources)


def test_recall_candidates_can_limit_results() -> None:
    dataset = load_low_altitude_economy_fixture()

    result = recall_candidates("低空经济", dataset, max_candidates=3)

    assert [candidate.company.symbol for candidate in result.candidates] == [
        "999001.SZ",
        "999002.SZ",
        "999003.SH",
    ]
    assert result.pipeline.output_count == 3

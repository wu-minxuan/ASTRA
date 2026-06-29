from astra.theme_research import load_low_altitude_economy_fixture
from astra.theme_research.contracts import (
    ConceptBoardRecord,
    ConceptConstituentRecord,
    ProviderMetadata,
    StockSourceRecord,
)
from astra.theme_research.market_data import ProviderUnavailableError
from astra.theme_research.recall import (
    normalize_theme_query,
    recall_candidates,
    recall_candidates_from_provider,
)


def make_provider_metadata(is_fallback: bool = False) -> ProviderMetadata:
    return ProviderMetadata(
        provider_name="akshare",
        provider_interface="unit_test_provider",
        retrieved_at="2026-06-29T00:00:00+00:00",
        is_fallback=is_fallback,
    )


class FakeMarketDataProvider:
    def list_stock_source_records(self) -> list[StockSourceRecord]:
        return []

    def list_concept_boards(self) -> list[ConceptBoardRecord]:
        metadata = make_provider_metadata()
        return [
            ConceptBoardRecord(
                raw_name="低空经济",
                concept_name="低空经济",
                board_code="BK1166",
                provider=metadata,
            ),
            ConceptBoardRecord(
                raw_name="飞行汽车(eVTOL)",
                concept_name="飞行汽车(eVTOL)",
                board_code="BK1157",
                provider=metadata,
            ),
            ConceptBoardRecord(
                raw_name="机器人",
                concept_name="机器人",
                board_code="BK0001",
                provider=metadata,
            ),
        ]

    def list_concept_constituents(
        self,
        concept_name: str,
    ) -> list[ConceptConstituentRecord]:
        metadata = make_provider_metadata()
        records = {
            "低空经济": [
                ConceptConstituentRecord(
                    concept_name="低空经济",
                    raw_symbol="300001",
                    symbol="300001.SZ",
                    name="真实低空一号",
                    exchange="SZSE",
                    industry="航空装备",
                    provider=metadata,
                ),
                ConceptConstituentRecord(
                    concept_name="低空经济",
                    raw_symbol="600001",
                    symbol="600001.SH",
                    name="真实低空二号",
                    exchange="SSE",
                    industry="通用设备",
                    provider=metadata,
                ),
            ],
            "飞行汽车(eVTOL)": [
                ConceptConstituentRecord(
                    concept_name="飞行汽车(eVTOL)",
                    raw_symbol="300001",
                    symbol="300001.SZ",
                    name="真实低空一号",
                    exchange="SZSE",
                    industry="航空装备",
                    provider=metadata,
                )
            ],
        }
        return records.get(concept_name, [])


class FailingMarketDataProvider(FakeMarketDataProvider):
    def list_concept_boards(self) -> list[ConceptBoardRecord]:
        raise ProviderUnavailableError("concept board list failed")

    def list_concept_constituents(
        self,
        concept_name: str,
    ) -> list[ConceptConstituentRecord]:
        raise ProviderUnavailableError(f"concept constituent failed: {concept_name}")


class EmptyMarketDataProvider(FakeMarketDataProvider):
    def list_concept_boards(self) -> list[ConceptBoardRecord]:
        return []

    def list_concept_constituents(
        self,
        concept_name: str,
    ) -> list[ConceptConstituentRecord]:
        return []


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
    assert result.candidates[0].fixture_company is not None
    assert result.candidates[0].company.provider.provider_name == "fixture"


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


def test_recall_candidates_from_provider_matches_concept_boards() -> None:
    dataset = load_low_altitude_economy_fixture()

    result = recall_candidates_from_provider(
        "低空经济",
        FakeMarketDataProvider(),
        fallback_dataset=dataset,
    )
    symbols = [candidate.company.symbol for candidate in result.candidates]
    first_candidate = result.candidates[0]

    assert result.matched_aliases == ["低空经济"]
    assert result.matched_concept_boards == ["低空经济", "飞行汽车(eVTOL)"]
    assert symbols == ["300001.SZ", "600001.SH"]
    assert first_candidate.company.concepts == ["低空经济", "飞行汽车(eVTOL)"]
    assert first_candidate.recall_score == 100
    assert first_candidate.fixture_company is None
    assert first_candidate.company.provider.provider_name == "akshare"


def test_recall_candidates_from_provider_can_limit_results() -> None:
    dataset = load_low_altitude_economy_fixture()

    result = recall_candidates_from_provider(
        "低空经济",
        FakeMarketDataProvider(),
        fallback_dataset=dataset,
        max_candidates=1,
    )

    assert [candidate.company.symbol for candidate in result.candidates] == ["300001.SZ"]
    assert result.pipeline.output_count == 1


def test_recall_candidates_from_provider_falls_back_to_fixture_on_failure() -> None:
    dataset = load_low_altitude_economy_fixture()

    result = recall_candidates_from_provider(
        "低空经济",
        FailingMarketDataProvider(),
        fallback_dataset=dataset,
        max_candidates=2,
    )

    assert [candidate.company.symbol for candidate in result.candidates] == [
        "999001.SZ",
        "999002.SZ",
    ]
    assert result.candidates[0].company.provider.provider_name == "fixture"
    assert result.candidates[0].fixture_company is not None
    assert "fixture fallback used for candidate recall" in result.warnings


def test_recall_candidates_from_provider_returns_empty_without_fallback() -> None:
    result = recall_candidates_from_provider(
        "不存在的主题",
        EmptyMarketDataProvider(),
    )

    assert result.candidates == []
    assert result.pipeline.output_count == 0
    assert result.warnings == ["concept constituents empty for 不存在的主题"]

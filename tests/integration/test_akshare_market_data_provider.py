from astra.theme_research.fixtures import load_low_altitude_economy_fixture
from astra.theme_research.market_data import AkshareMarketDataProvider
from astra.theme_research.recall import recall_candidates_from_provider


def test_live_akshare_stock_source_records_are_fetched_and_normalized() -> None:
    provider = AkshareMarketDataProvider()

    records = provider.list_stock_source_records()

    assert len(records) > 1000
    assert any(record.symbol == "000001.SZ" for record in records)
    assert all(record.symbol.endswith((".SZ", ".SH")) for record in records[:100])
    assert all(record.provider.provider_name == "akshare" for record in records[:100])
    assert all(
        record.provider.provider_interface == "stock_info_a_code_name"
        for record in records[:100]
    )


def test_live_akshare_low_altitude_concept_recall_returns_candidates() -> None:
    provider = AkshareMarketDataProvider()
    dataset = load_low_altitude_economy_fixture()

    result = recall_candidates_from_provider(
        "低空经济",
        provider,
        fallback_dataset=dataset,
        max_candidates=5,
    )

    assert len(result.candidates) == 5
    assert "低空经济" in result.matched_concept_boards
    assert all(
        candidate.company.provider.provider_name == "akshare"
        for candidate in result.candidates
    )
    assert all(candidate.fixture_company is None for candidate in result.candidates)
    assert all(
        any(match.source == "provider_concept_board" for match in candidate.matches)
        for candidate in result.candidates
    )

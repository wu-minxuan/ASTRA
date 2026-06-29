import pytest

from astra.theme_research.contracts import ProviderMetadata
from astra.theme_research.fixtures import load_low_altitude_economy_fixture
from astra.theme_research.market_data import (
    AkshareMarketDataProvider,
    FallbackMarketDataProvider,
    FixtureMarketDataProvider,
    ProviderDataError,
    ProviderUnavailableError,
    concept_board_record_from_row,
    concept_constituent_record_from_row,
    market_data_company_from_concept_record,
    market_data_company_from_stock_record,
    normalize_a_share_symbol,
    stock_source_record_from_row,
)


class FakeAkshareClient:
    def stock_info_a_code_name(self) -> list[dict[str, object]]:
        return [
            {"code": "000001", "name": "平安银行", "industry": "银行"},
            {"代码": "600519", "名称": "贵州茅台", "所属行业": "白酒"},
            {"code": "920000", "name": "北交所样例", "industry": "测试"},
        ]

    def stock_board_concept_name_em(self) -> list[dict[str, object]]:
        return [
            {"板块名称": "低空经济", "板块代码": "BK1166"},
            {"name": "飞行汽车(eVTOL)", "code": "BK1157"},
        ]

    def stock_board_concept_cons_em(self, symbol: str) -> list[dict[str, object]]:
        return [
            {"代码": "300750", "名称": "宁德时代", "所属行业": "电池", "概念": symbol}
        ]


class FailingMarketDataProvider:
    def list_stock_source_records(self) -> list[object]:
        raise ProviderUnavailableError("primary stock provider failed")

    def list_concept_boards(self) -> list[object]:
        raise ProviderUnavailableError("primary concept boards failed")

    def list_concept_constituents(self, concept_name: str) -> list[object]:
        raise ProviderUnavailableError(f"primary concept provider failed: {concept_name}")


class EmptyMarketDataProvider:
    def list_stock_source_records(self) -> list[object]:
        return []

    def list_concept_boards(self) -> list[object]:
        return []

    def list_concept_constituents(self, concept_name: str) -> list[object]:
        return []


def make_metadata() -> ProviderMetadata:
    return ProviderMetadata(
        provider_name="akshare",
        provider_interface="unit_test_interface",
        retrieved_at="2026-06-16T00:00:00+00:00",
    )


def test_normalizes_supported_a_share_symbols() -> None:
    assert normalize_a_share_symbol("000001") == "000001.SZ"
    assert normalize_a_share_symbol("SZ000001") == "000001.SZ"
    assert normalize_a_share_symbol("600519") == "600519.SH"
    assert normalize_a_share_symbol("600519.SH") == "600519.SH"


def test_rejects_unsupported_phase_1_exchange() -> None:
    with pytest.raises(ProviderDataError, match="unsupported Phase 1 stock exchange"):
        normalize_a_share_symbol("430001")


def test_maps_provider_stock_row_to_internal_company() -> None:
    record = stock_source_record_from_row(
        {"代码": "000001", "名称": "平安银行", "所属行业": "银行"},
        make_metadata(),
    )

    assert record.symbol == "000001.SZ"
    assert record.exchange == "SZSE"
    assert record.provider.provider_name == "akshare"

    company = market_data_company_from_stock_record(record)

    assert company.symbol == "000001.SZ"
    assert company.name == "平安银行"
    assert company.industry == "银行"
    assert company.concepts == []


def test_maps_provider_concept_board_row() -> None:
    record = concept_board_record_from_row(
        {"板块名称": "低空经济", "板块代码": "BK1166"},
        make_metadata(),
    )

    assert record.concept_name == "低空经济"
    assert record.board_code == "BK1166"
    assert record.provider.provider_name == "akshare"


def test_maps_provider_concept_row_to_internal_company() -> None:
    record = concept_constituent_record_from_row(
        {"代码": "600519", "名称": "贵州茅台", "所属行业": "白酒"},
        "消费升级",
        make_metadata(),
    )

    company = market_data_company_from_concept_record(record)

    assert company.symbol == "600519.SH"
    assert company.exchange == "SSE"
    assert company.concepts == ["消费升级"]


def test_provider_row_mapping_requires_symbol_and_name() -> None:
    with pytest.raises(ProviderDataError, match="provider row missing required fields"):
        stock_source_record_from_row({"名称": "缺代码公司"}, make_metadata())

    with pytest.raises(ProviderDataError, match="provider row missing required fields"):
        concept_constituent_record_from_row({"代码": "000001"}, "银行", make_metadata())


def test_akshare_provider_uses_injected_client_without_network() -> None:
    provider = AkshareMarketDataProvider(
        client=FakeAkshareClient(),
        retrieved_at_factory=lambda: "2026-06-16T00:00:00+00:00",
    )

    stock_records = provider.list_stock_source_records()
    concept_boards = provider.list_concept_boards()
    concept_records = provider.list_concept_constituents("新能源车")

    assert [record.symbol for record in stock_records] == ["000001.SZ", "600519.SH"]
    assert stock_records[0].provider.provider_interface == "stock_info_a_code_name"
    assert [record.concept_name for record in concept_boards] == [
        "低空经济",
        "飞行汽车(eVTOL)",
    ]
    assert concept_boards[0].provider.provider_interface == "stock_board_concept_name_em"
    assert concept_records[0].symbol == "300750.SZ"
    assert concept_records[0].concept_name == "新能源车"
    assert concept_records[0].provider.provider_interface == "stock_board_concept_cons_em"


def test_fixture_provider_returns_fallback_stock_and_concept_records() -> None:
    dataset = load_low_altitude_economy_fixture()
    provider = FixtureMarketDataProvider(dataset)

    stock_records = provider.list_stock_source_records()
    concept_boards = provider.list_concept_boards()
    concept_records = provider.list_concept_constituents("低空经济")

    assert len(stock_records) == len(dataset.companies)
    assert concept_boards[0].concept_name == "低空经济"
    assert all(record.provider.is_fallback is True for record in concept_boards)
    assert len(concept_records) == len(dataset.companies)
    assert stock_records[0].provider.provider_name == "fixture"
    assert stock_records[0].provider.is_fallback is True
    assert concept_records[0].concept_name == "低空经济"


def test_fallback_provider_uses_fixture_when_primary_fails() -> None:
    dataset = load_low_altitude_economy_fixture()
    provider = FallbackMarketDataProvider(
        primary=FailingMarketDataProvider(),
        fallback=FixtureMarketDataProvider(dataset),
    )

    stock_records = provider.list_stock_source_records()
    concept_boards = provider.list_concept_boards()
    concept_records = provider.list_concept_constituents("低空经济")

    assert len(stock_records) == len(dataset.companies)
    assert stock_records[0].provider.is_fallback is True
    assert stock_records[0].provider.failure_reason == "primary stock provider failed"
    assert concept_boards[0].provider.failure_reason == "primary concept boards failed"
    assert concept_records[0].provider.failure_reason == (
        "primary concept provider failed: 低空经济"
    )


def test_fallback_provider_uses_fixture_when_primary_returns_empty() -> None:
    dataset = load_low_altitude_economy_fixture()
    provider = FallbackMarketDataProvider(
        primary=EmptyMarketDataProvider(),
        fallback=FixtureMarketDataProvider(dataset),
    )

    stock_records = provider.list_stock_source_records()
    concept_boards = provider.list_concept_boards()
    concept_records = provider.list_concept_constituents("低空经济")

    assert stock_records[0].provider.failure_reason == (
        "primary provider returned no stock records"
    )
    assert concept_boards[0].provider.failure_reason == (
        "primary provider returned no concept boards"
    )
    assert concept_records[0].provider.failure_reason == (
        "primary provider returned no concept constituents"
    )

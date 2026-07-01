import pytest

from astra.theme_research.contracts import ProviderMetadata
from astra.theme_research.fixtures import load_low_altitude_economy_fixture
from astra.theme_research.market_data import (
    AkshareMarketDataProvider,
    FallbackMarketDataProvider,
    FixtureMarketDataProvider,
    ProviderDataError,
    ProviderUnavailableError,
    business_profile_record_from_row,
    concept_board_record_from_row,
    concept_constituent_record_from_row,
    financial_snapshot_record_from_rows,
    financial_statement_record_from_rows,
    market_data_company_from_concept_record,
    market_data_company_from_stock_record,
    normalize_a_share_symbol,
    provider_market_symbol,
    provider_stock_code,
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

    def stock_zyjs_ths(self, symbol: str) -> list[dict[str, object]]:
        return [
            {
                "股票代码": symbol,
                "主营业务": "动力电池系统业务。",
                "产品类型": "电池",
                "产品名称": "动力电池",
                "经营范围": "新能源技术开发。",
            }
        ]

    def stock_financial_abstract(self, symbol: str) -> list[dict[str, object]]:
        return [
            {"指标": "营业总收入", "20260331": "1000"},
            {"指标": "归母净利润", "20260331": "120"},
            {"指标": "净利润", "20260331": "118"},
            {"指标": "无关指标", "20260331": "999"},
        ]

    def stock_balance_sheet_by_report_em(self, symbol: str) -> list[dict[str, object]]:
        return [
            {
                "SECUCODE": "300750.SZ",
                "REPORT_DATE": "2026-03-31 00:00:00",
                "TOTAL_ASSETS": 1000.0,
                "IGNORED_NAN": float("nan"),
            }
        ]

    def stock_profit_sheet_by_report_em(self, symbol: str) -> list[dict[str, object]]:
        return [
            {
                "SECUCODE": "300750.SZ",
                "REPORT_DATE": "2026-03-31 00:00:00",
                "OPERATE_INCOME": 500.0,
            }
        ]

    def stock_cash_flow_sheet_by_report_em(self, symbol: str) -> list[dict[str, object]]:
        return [
            {
                "SECUCODE": "300750.SZ",
                "REPORT_DATE": "2026-03-31 00:00:00",
                "NETCASH_OPERATE": 80.0,
            }
        ]


class FailingMarketDataProvider:
    def list_stock_source_records(self) -> list[object]:
        raise ProviderUnavailableError("primary stock provider failed")

    def list_concept_boards(self) -> list[object]:
        raise ProviderUnavailableError("primary concept boards failed")

    def list_concept_constituents(self, concept_name: str) -> list[object]:
        raise ProviderUnavailableError(f"primary concept provider failed: {concept_name}")

    def get_business_profile(self, symbol: str) -> object:
        raise ProviderUnavailableError(f"primary business provider failed: {symbol}")

    def get_financial_snapshot(self, symbol: str) -> object:
        raise ProviderUnavailableError(f"primary financial provider failed: {symbol}")

    def get_financial_statement(self, symbol: str, statement_type: str) -> object:
        raise ProviderUnavailableError(
            f"primary financial statement provider failed: {symbol}: {statement_type}"
        )


class EmptyMarketDataProvider:
    def list_stock_source_records(self) -> list[object]:
        return []

    def list_concept_boards(self) -> list[object]:
        return []

    def list_concept_constituents(self, concept_name: str) -> list[object]:
        return []

    def get_business_profile(self, symbol: str) -> object:
        return {}

    def get_financial_snapshot(self, symbol: str) -> object:
        return {}

    def get_financial_statement(self, symbol: str, statement_type: str) -> object:
        return {}


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
    assert provider_stock_code("000001.SZ") == "000001"
    assert provider_market_symbol("000001.SZ") == "SZ000001"
    assert provider_market_symbol("600519.SH") == "SH600519"


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


def test_maps_provider_business_profile_row() -> None:
    record = business_profile_record_from_row(
        {
            "股票代码": "300750",
            "主营业务": "动力电池系统业务。",
            "产品类型": "电池",
            "产品名称": "动力电池",
            "经营范围": "新能源技术开发。",
        },
        "300750",
        make_metadata(),
    )

    assert record.symbol == "300750.SZ"
    assert record.main_business == "动力电池系统业务。"
    assert record.product_type == "电池"
    assert record.provider.provider_name == "akshare"


def test_maps_provider_financial_snapshot_rows() -> None:
    record = financial_snapshot_record_from_rows(
        [
            {"指标": "营业总收入", "20260331": "1000", "20251231": "900"},
            {"指标": "归母净利润", "20260331": "120", "20251231": "100"},
            {"指标": "无关指标", "20260331": "999"},
        ],
        "300750",
        make_metadata(),
    )

    assert record.symbol == "300750.SZ"
    assert record.report_period == "20260331"
    assert record.metrics == {"营业总收入": "1000", "归母净利润": "120"}


def test_maps_provider_financial_statement_rows_without_dropping_fields() -> None:
    record = financial_statement_record_from_rows(
        [
            {
                "REPORT_DATE": "2026-03-31 00:00:00",
                "TOTAL_ASSETS": 1000.0,
                "TOTAL_ASSETS_YOY": 5.5,
                "EMPTY": float("nan"),
            }
        ],
        "300750",
        "balance_sheet",
        make_metadata(),
    )

    assert record.symbol == "300750.SZ"
    assert record.statement_type == "balance_sheet"
    assert record.columns == ["REPORT_DATE", "TOTAL_ASSETS", "TOTAL_ASSETS_YOY"]
    assert record.rows == [
        {
            "REPORT_DATE": "2026-03-31 00:00:00",
            "TOTAL_ASSETS": 1000.0,
            "TOTAL_ASSETS_YOY": 5.5,
        }
    ]


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
    business_profile = provider.get_business_profile("300750.SZ")
    financial_snapshot = provider.get_financial_snapshot("300750.SZ")
    balance_sheet = provider.get_financial_statement("300750.SZ", "balance_sheet")
    income_statement = provider.get_financial_statement("300750.SZ", "income_statement")
    cash_flow_statement = provider.get_financial_statement("300750.SZ", "cash_flow_statement")

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
    assert business_profile.main_business == "动力电池系统业务。"
    assert business_profile.provider.provider_interface == "stock_zyjs_ths"
    assert financial_snapshot.report_period == "20260331"
    assert financial_snapshot.provider.provider_interface == "stock_financial_abstract"
    assert balance_sheet.provider.provider_interface == "stock_balance_sheet_by_report_em"
    assert balance_sheet.rows[0]["TOTAL_ASSETS"] == 1000.0
    assert "IGNORED_NAN" not in balance_sheet.rows[0]
    assert income_statement.rows[0]["OPERATE_INCOME"] == 500.0
    assert cash_flow_statement.rows[0]["NETCASH_OPERATE"] == 80.0


def test_fixture_provider_returns_fallback_stock_and_concept_records() -> None:
    dataset = load_low_altitude_economy_fixture()
    provider = FixtureMarketDataProvider(dataset)

    stock_records = provider.list_stock_source_records()
    concept_boards = provider.list_concept_boards()
    concept_records = provider.list_concept_constituents("低空经济")
    business_profile = provider.get_business_profile(dataset.companies[0].symbol)
    financial_snapshot = provider.get_financial_snapshot(dataset.companies[0].symbol)
    balance_sheet = provider.get_financial_statement(
        dataset.companies[0].symbol,
        "balance_sheet",
    )

    assert len(stock_records) == len(dataset.companies)
    assert concept_boards[0].concept_name == "低空经济"
    assert all(record.provider.is_fallback is True for record in concept_boards)
    assert len(concept_records) == len(dataset.companies)
    assert stock_records[0].provider.provider_name == "fixture"
    assert stock_records[0].provider.is_fallback is True
    assert concept_records[0].concept_name == "低空经济"
    assert business_profile.main_business == dataset.companies[0].business_summary
    assert financial_snapshot.metrics == {
        "fixture_financial_summary": dataset.companies[0].financial_summary
    }
    assert balance_sheet.statement_type == "balance_sheet"
    assert balance_sheet.provider.is_fallback is True


def test_fallback_provider_uses_fixture_when_primary_fails() -> None:
    dataset = load_low_altitude_economy_fixture()
    provider = FallbackMarketDataProvider(
        primary=FailingMarketDataProvider(),
        fallback=FixtureMarketDataProvider(dataset),
    )

    stock_records = provider.list_stock_source_records()
    concept_boards = provider.list_concept_boards()
    concept_records = provider.list_concept_constituents("低空经济")
    business_profile = provider.get_business_profile(dataset.companies[0].symbol)
    financial_snapshot = provider.get_financial_snapshot(dataset.companies[0].symbol)
    financial_statement = provider.get_financial_statement(
        dataset.companies[0].symbol,
        "balance_sheet",
    )

    assert len(stock_records) == len(dataset.companies)
    assert stock_records[0].provider.is_fallback is True
    assert stock_records[0].provider.failure_reason == "primary stock provider failed"
    assert concept_boards[0].provider.failure_reason == "primary concept boards failed"
    assert concept_records[0].provider.failure_reason == (
        "primary concept provider failed: 低空经济"
    )
    assert business_profile.provider.failure_reason == (
        f"primary business provider failed: {dataset.companies[0].symbol}"
    )
    assert financial_snapshot.provider.failure_reason == (
        f"primary financial provider failed: {dataset.companies[0].symbol}"
    )
    assert financial_statement.provider.failure_reason == (
        "primary financial statement provider failed: "
        f"{dataset.companies[0].symbol}: balance_sheet"
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

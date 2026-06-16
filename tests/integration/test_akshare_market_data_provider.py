from astra.theme_research.market_data import AkshareMarketDataProvider


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

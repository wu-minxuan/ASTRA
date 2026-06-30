from astra.theme_research.contracts import (
    BusinessProfileRecord,
    ConceptConstituentRecord,
    FinancialSnapshotRecord,
    ProviderMetadata,
    StockSourceRecord,
)
from astra.theme_research.market_data import ProviderUnavailableError
from astra.theme_research.market_metadata import (
    MarketMetadataBackedProvider,
    MarketMetadataStore,
)


def make_metadata(provider_interface: str) -> ProviderMetadata:
    return ProviderMetadata(
        provider_name="akshare",
        provider_interface=provider_interface,
        retrieved_at="2026-06-30T00:00:00+00:00",
    )


class LiveConceptProvider:
    def __init__(self) -> None:
        self.concept_queries: list[str] = []

    def list_stock_source_records(self) -> list[StockSourceRecord]:
        return []

    def list_concept_boards(self) -> list[object]:
        raise AssertionError("metadata-backed provider should not call live board discovery")

    def list_concept_constituents(
        self,
        concept_name: str,
    ) -> list[ConceptConstituentRecord]:
        self.concept_queries.append(concept_name)
        return [
            ConceptConstituentRecord(
                concept_name=concept_name,
                raw_symbol="300001",
                symbol="300001.SZ",
                name="真实低空一号",
                exchange="SZSE",
                industry="航空装备",
                provider=make_metadata("stock_board_concept_cons_em"),
            )
        ]

    def get_business_profile(self, symbol: str) -> BusinessProfileRecord:
        return BusinessProfileRecord(
            raw_symbol=symbol[:6],
            symbol=symbol,
            main_business="低空飞行器核心部件。",
            provider=make_metadata("stock_zyjs_ths"),
        )

    def get_financial_snapshot(self, symbol: str) -> FinancialSnapshotRecord:
        return FinancialSnapshotRecord(
            raw_symbol=symbol[:6],
            symbol=symbol,
            report_period="20260331",
            metrics={"营业总收入": "1000"},
            provider=make_metadata("stock_financial_abstract"),
        )


class FailingConceptProvider(LiveConceptProvider):
    def list_concept_constituents(
        self,
        concept_name: str,
    ) -> list[ConceptConstituentRecord]:
        self.concept_queries.append(concept_name)
        raise ProviderUnavailableError(f"live concept failed: {concept_name}")


def test_default_market_metadata_store_loads_seed_boards() -> None:
    store = MarketMetadataStore.load()

    boards = store.list_concept_boards()
    low_altitude = store.find_concept_board("低空经济")
    evtol = store.find_concept_board("eVTOL")

    assert low_altitude is not None
    assert low_altitude.board_code == "BK1166"
    assert evtol is not None
    assert evtol.board_code == "BK1157"
    assert any(board.concept_name == "低空" for board in boards)


def test_metadata_backed_provider_uses_board_code_for_live_constituents() -> None:
    primary = LiveConceptProvider()
    provider = MarketMetadataBackedProvider(primary=primary)

    records = provider.list_concept_constituents("低空经济")

    assert primary.concept_queries == ["BK1166"]
    assert [record.concept_name for record in records] == ["低空经济"]
    assert records[0].provider.provider_interface == "stock_board_concept_cons_em"
    assert records[0].provider.is_fallback is False


def test_metadata_backed_provider_returns_cached_constituents_when_live_fails() -> None:
    primary = FailingConceptProvider()
    provider = MarketMetadataBackedProvider(primary=primary)

    records = provider.list_concept_constituents("低空经济")

    assert primary.concept_queries == ["BK1166"]
    assert len(records) >= 5
    assert records[0].concept_name == "低空经济"
    assert records[0].provider.is_fallback is True
    assert records[0].provider.failure_reason == "live concept failed: BK1166"
    assert records[0].provider.provider_interface.startswith("market_metadata_cache:")

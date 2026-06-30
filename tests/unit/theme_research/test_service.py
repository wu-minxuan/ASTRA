import pytest

from astra.theme_research.contracts import (
    BusinessProfileRecord,
    ConceptBoardRecord,
    ConceptConstituentRecord,
    FinancialSnapshotRecord,
    ProviderMetadata,
    StockSourceRecord,
    ThemeResearchRequest,
)
from astra.theme_research.market_data import AkshareMarketDataProvider, ProviderUnavailableError
from astra.theme_research.market_metadata import MarketMetadataBackedProvider
from astra.theme_research.recall_signal_scoring import (
    FakeRecallSignalScorer,
    RecallSignalScoringError,
)
from astra.theme_research.service import ThemeResearchServiceError, run_theme_research


def make_metadata(provider_interface: str) -> ProviderMetadata:
    return ProviderMetadata(
        provider_name="akshare",
        provider_interface=provider_interface,
        retrieved_at="2026-06-30T00:00:00+00:00",
    )


class FakeLiveMarketDataProvider:
    def list_stock_source_records(self) -> list[StockSourceRecord]:
        return []

    def list_concept_boards(self) -> list[ConceptBoardRecord]:
        return [
            ConceptBoardRecord(
                raw_name="低空经济",
                concept_name="低空经济",
                board_code="BK1166",
                provider=make_metadata("stock_board_concept_name_em"),
            )
        ]

    def list_concept_constituents(
        self,
        concept_name: str,
    ) -> list[ConceptConstituentRecord]:
        if concept_name != "低空经济":
            return []
        return [
            ConceptConstituentRecord(
                concept_name="低空经济",
                raw_symbol="300001",
                symbol="300001.SZ",
                name="真实低空一号",
                exchange="SZSE",
                industry="航空装备",
                provider=make_metadata("stock_board_concept_cons_em"),
            ),
            ConceptConstituentRecord(
                concept_name="低空经济",
                raw_symbol="600001",
                symbol="600001.SH",
                name="真实低空二号",
                exchange="SSE",
                industry="通用设备",
                provider=make_metadata("stock_board_concept_cons_em"),
            ),
        ]

    def get_business_profile(self, symbol: str) -> BusinessProfileRecord:
        return BusinessProfileRecord(
            raw_symbol=symbol[:6],
            symbol=symbol,
            main_business="低空飞行器核心部件和系统集成。",
            product_type="航空装备",
            product_name="飞控系统",
            business_scope="低空飞行器技术服务。",
            provider=make_metadata("stock_zyjs_ths"),
        )

    def get_financial_snapshot(self, symbol: str) -> FinancialSnapshotRecord:
        return FinancialSnapshotRecord(
            raw_symbol=symbol[:6],
            symbol=symbol,
            report_period="20260331",
            metrics={"营业总收入": "1000", "归母净利润": "120"},
            provider=make_metadata("stock_financial_abstract"),
        )


class EmptyMarketDataProvider(FakeLiveMarketDataProvider):
    def list_concept_boards(self) -> list[ConceptBoardRecord]:
        return [
            ConceptBoardRecord(
                raw_name="机器人",
                concept_name="机器人",
                board_code="BK0001",
                provider=make_metadata("stock_board_concept_name_em"),
            )
        ]

    def list_concept_constituents(
        self,
        concept_name: str,
    ) -> list[ConceptConstituentRecord]:
        return []


class ManyCandidateMarketDataProvider(FakeLiveMarketDataProvider):
    def list_concept_constituents(
        self,
        concept_name: str,
    ) -> list[ConceptConstituentRecord]:
        if concept_name != "低空经济":
            return []
        return [
            ConceptConstituentRecord(
                concept_name="低空经济",
                raw_symbol=f"300{index:03d}",
                symbol=f"300{index:03d}.SZ",
                name=f"真实低空{index:02d}",
                exchange="SZSE",
                industry="航空装备",
                provider=make_metadata("stock_board_concept_cons_em"),
            )
            for index in range(1, 11)
        ]


class FailingAkshareClient:
    def stock_board_concept_name_em(self) -> object:
        raise RuntimeError("RemoteDisconnected: remote end closed connection without response")

    def stock_board_concept_cons_em(self, symbol: str) -> object:
        raise RuntimeError(f"RemoteDisconnected for {symbol}")


class FailingConceptProviderWithEvidence(FakeLiveMarketDataProvider):
    def list_concept_boards(self) -> list[ConceptBoardRecord]:
        raise AssertionError("metadata-backed provider should not call live board discovery")

    def list_concept_constituents(
        self,
        concept_name: str,
    ) -> list[ConceptConstituentRecord]:
        raise ProviderUnavailableError(f"live concept failed: {concept_name}")


class FailingRecallSignalScorer(FakeRecallSignalScorer):
    def score_candidate(self, **_: object):
        raise RecallSignalScoringError("DeepSeek unavailable in unit test")


class CountingRecallSignalScorer(FakeRecallSignalScorer):
    def __init__(self) -> None:
        self.scored_symbols: list[str] = []

    def score_candidate(self, **kwargs: object):
        candidate = kwargs["candidate"]
        self.scored_symbols.append(candidate.company.symbol)
        return super().score_candidate(**kwargs)


def test_run_theme_research_uses_provider_backed_recall_without_fixture() -> None:
    response = run_theme_research(
        ThemeResearchRequest(theme="低空经济", max_results=2),
        market_data_provider=FakeLiveMarketDataProvider(),
        recall_signal_scorer=FakeRecallSignalScorer(),
    )

    assert response.request.normalized_query == "低空经济"
    assert [candidate.name for candidate in response.result.pool] == [
        "真实低空一号",
        "真实低空二号",
    ]
    assert response.result.report is not None
    assert all(
        evidence.source_type != "fixture"
        for candidate in response.result.pool
        for evidence in candidate.evidence
    )
    assert any("akshare market data" in item for item in response.result.data_boundary)


def test_run_theme_research_caps_candidates_before_recall_signal_scoring() -> None:
    scorer = CountingRecallSignalScorer()

    run_theme_research(
        ThemeResearchRequest(theme="低空经济", max_results=2, include_report=False),
        market_data_provider=ManyCandidateMarketDataProvider(),
        recall_signal_scorer=scorer,
    )

    assert scorer.scored_symbols == [
        "300001.SZ",
        "300002.SZ",
        "300003.SZ",
        "300004.SZ",
        "300005.SZ",
        "300006.SZ",
    ]


def test_run_theme_research_reports_provider_unavailable_without_fixture_fallback() -> None:
    provider = AkshareMarketDataProvider(client=FailingAkshareClient())

    with pytest.raises(ThemeResearchServiceError) as exc_info:
        run_theme_research(
            ThemeResearchRequest(theme="低空经济"),
            market_data_provider=provider,
        )

    error = exc_info.value
    assert error.code == "provider_unavailable"
    assert error.details["provider"] == "akshare"
    assert error.details["stage"] == "candidate_recall"
    assert "stock_board_concept_name_em" in error.details["error_message"]


def test_run_theme_research_can_use_cached_market_metadata_when_live_concepts_fail() -> None:
    response = run_theme_research(
        ThemeResearchRequest(theme="低空经济", max_results=2, include_report=False),
        market_data_provider=MarketMetadataBackedProvider(
            primary=FailingConceptProviderWithEvidence()
        ),
        recall_signal_scorer=FakeRecallSignalScorer(),
    )

    assert response.request.normalized_query == "低空经济"
    assert len(response.result.pool) == 2
    assert response.result.report is None
    assert all(
        candidate.evidence[0].source_name.startswith("akshare:")
        for candidate in response.result.pool
    )
    assert any("cached market metadata snapshot" in item for item in response.result.data_boundary)


def test_run_theme_research_reports_model_unavailable_without_fake_fallback() -> None:
    with pytest.raises(ThemeResearchServiceError) as exc_info:
        run_theme_research(
            ThemeResearchRequest(theme="低空经济", max_results=2),
            market_data_provider=FakeLiveMarketDataProvider(),
            recall_signal_scorer=FailingRecallSignalScorer(),
        )

    error = exc_info.value
    assert error.code == "model_unavailable"
    assert error.details["stage"] == "candidate_recall"
    assert error.details["model_provider"] == "deepseek"
    assert "DeepSeek unavailable" in error.details["error_message"]


def test_run_theme_research_keeps_no_candidates_distinct_from_provider_failure() -> None:
    with pytest.raises(ThemeResearchServiceError) as exc_info:
        run_theme_research(
            ThemeResearchRequest(theme="完全不存在的主题"),
            market_data_provider=EmptyMarketDataProvider(),
        )

    error = exc_info.value
    assert error.code == "no_candidates"
    assert error.details["normalized_query"] == "完全不存在的主题"
    assert error.details["warnings"] == ["concept constituents empty for 完全不存在的主题"]

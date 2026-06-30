from astra.theme_research.contracts import (
    MarketDataCompany,
    ProviderMetadata,
    RecalledCandidate,
    RecallMatch,
)
from astra.theme_research.evidence import enrich_recalled_candidate
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


def test_live_akshare_provider_evidence_enrichment_returns_core_evidence() -> None:
    provider = AkshareMarketDataProvider()
    candidate = RecalledCandidate(
        company=MarketDataCompany(
            symbol="000001.SZ",
            name="平安银行",
            exchange="SZSE",
            industry="银行",
            concepts=["银行"],
            provider=ProviderMetadata(
                provider_name="akshare",
                provider_interface="integration_test_seed",
                retrieved_at="2026-06-30T00:00:00+00:00",
            ),
        ),
        matches=[
            RecallMatch(
                source="provider_concept_board",
                term="银行",
                reason="集成测试种子候选，用于验证真实 AKShare 证据补全。",
            )
        ],
        recall_score=70,
    )

    enriched = enrich_recalled_candidate(candidate, provider=provider)
    evidence = enriched.evidence_package.evidence
    kinds = {item.kind for item in evidence}

    assert "business_summary" in kinds
    assert "financial_summary" in kinds
    assert any(item.source_name == "akshare:stock_zyjs_ths" for item in evidence)
    assert any(item.source_name == "akshare:stock_financial_abstract" for item in evidence)
    assert all(
        item.source_type == "market_data_provider"
        for item in evidence
        if item.source_name.startswith("akshare:")
    )

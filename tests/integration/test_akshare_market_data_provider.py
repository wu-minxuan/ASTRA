import pytest

from astra.theme_research.contracts import (
    MarketDataCompany,
    ProviderMetadata,
    RecalledCandidate,
    RecallMatch,
)
from astra.theme_research.evidence import enrich_recalled_candidate
from astra.theme_research.market_data import (
    CONCEPT_CONSTITUENTS_INTERFACE,
    AkshareMarketDataProvider,
)
from astra.theme_research.market_metadata import (
    MARKET_METADATA_CACHE_INTERFACE,
    MarketMetadataBackedProvider,
)
from astra.theme_research.recall import recall_candidates_from_provider

pytestmark = pytest.mark.live


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


def test_live_akshare_low_altitude_metadata_backed_recall_is_transparent() -> None:
    provider = MarketMetadataBackedProvider(AkshareMarketDataProvider())

    result = recall_candidates_from_provider(
        "低空经济",
        provider,
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
    assert all(
        any(signal.signal_type == "provider_concept_board" for signal in candidate.signals)
        for candidate in result.candidates
    )
    assert all(
        all(signal.source_type == "market_data_provider" for signal in candidate.signals)
        for candidate in result.candidates
    )

    candidate_metadata = [candidate.company.provider for candidate in result.candidates]
    assert all(
        metadata.provider_interface == CONCEPT_CONSTITUENTS_INTERFACE
        or metadata.provider_interface.startswith(f"{MARKET_METADATA_CACHE_INTERFACE}:")
        for metadata in candidate_metadata
    )
    cached_metadata = [
        metadata
        for metadata in candidate_metadata
        if metadata.provider_interface.startswith(f"{MARKET_METADATA_CACHE_INTERFACE}:")
    ]
    assert all(metadata.is_fallback for metadata in cached_metadata)
    assert all(metadata.failure_reason for metadata in cached_metadata)


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

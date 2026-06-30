from astra.theme_research.contracts import (
    BusinessProfileRecord,
    FinancialSnapshotRecord,
    MarketDataCompany,
    ProviderMetadata,
    RecalledCandidate,
    RecallMatch,
)
from astra.theme_research.evidence import (
    WEB_KNOWLEDGE_BOUNDARY,
    enrich_recalled_candidate,
    enrich_recalled_candidates,
)
from astra.theme_research.fixtures import load_low_altitude_economy_fixture
from astra.theme_research.recall import recall_candidates


def make_provider_metadata(
    provider_interface: str = "stock_board_concept_cons_em",
) -> ProviderMetadata:
    return ProviderMetadata(
        provider_name="akshare",
        provider_interface=provider_interface,
        retrieved_at="2026-06-30T00:00:00+00:00",
    )


def make_provider_candidate() -> RecalledCandidate:
    metadata = make_provider_metadata()
    return RecalledCandidate(
        company=MarketDataCompany(
            symbol="300001.SZ",
            name="真实低空一号",
            exchange="SZSE",
            industry="航空装备",
            concepts=["低空经济"],
            provider=metadata,
        ),
        matches=[
            RecallMatch(
                source="provider_concept_board",
                term="低空经济",
                reason="真实概念板块成分命中：低空经济",
            )
        ],
        recall_score=70,
    )


class FakeEvidenceProvider:
    def get_business_profile(self, symbol: str) -> BusinessProfileRecord:
        return BusinessProfileRecord(
            raw_symbol=symbol[:6],
            symbol=symbol,
            main_business="低空飞行器核心部件业务。",
            product_type="航空装备",
            product_name="飞控系统",
            business_scope="低空飞行器技术服务。",
            provider=make_provider_metadata("stock_zyjs_ths"),
        )

    def get_financial_snapshot(self, symbol: str) -> FinancialSnapshotRecord:
        return FinancialSnapshotRecord(
            raw_symbol=symbol[:6],
            symbol=symbol,
            report_period="20260331",
            metrics={"营业总收入": "1000", "归母净利润": "120"},
            provider=make_provider_metadata("stock_financial_abstract"),
        )


class FailingEvidenceProvider:
    def get_business_profile(self, symbol: str) -> BusinessProfileRecord:
        raise RuntimeError(f"business failed: {symbol}")

    def get_financial_snapshot(self, symbol: str) -> FinancialSnapshotRecord:
        raise RuntimeError(f"financial failed: {symbol}")


def test_enrich_recalled_candidates_builds_complete_fixture_package() -> None:
    dataset = load_low_altitude_economy_fixture()
    recall_result = recall_candidates("低空经济", dataset, max_candidates=1)

    result = enrich_recalled_candidates(recall_result)
    candidate = result.candidates[0]
    package = candidate.evidence_package
    kinds = {item.kind for item in package.evidence}

    assert result.pipeline.stage == "evidence_enrichment"
    assert result.pipeline.input_count == 1
    assert result.pipeline.output_count == 1
    assert candidate.fixture_company is not None
    assert package.missing_kinds == []
    assert {
        "concept",
        "industry",
        "business_summary",
        "financial_summary",
        "text_summary",
        "risk",
        "theme_relationship",
    }.issubset(kinds)
    assert all(
        item.source_type == "fixture"
        for item in package.evidence
        if item.source_name == "ASTRA Phase 1 fixture"
    )


def test_enrich_provider_candidate_uses_market_data_provider_evidence() -> None:
    candidate = make_provider_candidate()

    enriched = enrich_recalled_candidate(candidate, provider=FakeEvidenceProvider())
    package = enriched.evidence_package
    kinds = {item.kind for item in package.evidence}
    provider_source_types = {
        item.source_type
        for item in package.evidence
        if item.source_name.startswith("akshare:")
    }

    assert {
        "concept",
        "industry",
        "business_summary",
        "financial_summary",
        "theme_relationship",
    }.issubset(kinds)
    assert package.missing_kinds == ["text_summary", "risk"]
    assert provider_source_types == {"market_data_provider"}
    assert any("stock_zyjs_ths" in item.source_name for item in package.evidence)
    assert any("stock_financial_abstract" in item.source_name for item in package.evidence)
    assert WEB_KNOWLEDGE_BOUNDARY in package.data_boundary


def test_enrich_provider_candidate_records_provider_failures_and_missing_kinds() -> None:
    candidate = make_provider_candidate()

    enriched = enrich_recalled_candidate(candidate, provider=FailingEvidenceProvider())
    package = enriched.evidence_package

    assert package.missing_kinds == [
        "business_summary",
        "financial_summary",
        "text_summary",
        "risk",
    ]
    assert any(
        warning.startswith("business profile unavailable for 300001.SZ")
        for warning in package.warnings
    )
    assert any(
        warning.startswith("financial snapshot unavailable for 300001.SZ")
        for warning in package.warnings
    )
    assert any("evidence kinds missing for 300001.SZ" in warning for warning in package.warnings)

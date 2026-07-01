from astra.theme_research.contracts import (
    BusinessProfileRecord,
    FinancialSnapshotRecord,
    FinancialStatementRecord,
    MarketDataCompany,
    ProviderMetadata,
    RecalledCandidate,
    RecallMatch,
    WebKnowledgeRecord,
    WebKnowledgeResult,
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

    def get_financial_statement(
        self,
        symbol: str,
        statement_type: str,
    ) -> FinancialStatementRecord:
        return FinancialStatementRecord(
            raw_symbol=symbol[:6],
            symbol=symbol,
            statement_type=statement_type,
            columns=["REPORT_DATE", "FULL_FIELD"],
            rows=[
                {
                    "REPORT_DATE": "2026-03-31 00:00:00",
                    "FULL_FIELD": f"{statement_type}-value",
                }
            ],
            provider=make_provider_metadata(f"statement:{statement_type}"),
        )


class FailingEvidenceProvider:
    def get_business_profile(self, symbol: str) -> BusinessProfileRecord:
        raise RuntimeError(f"business failed: {symbol}")

    def get_financial_snapshot(self, symbol: str) -> FinancialSnapshotRecord:
        raise RuntimeError(f"financial failed: {symbol}")

    def get_financial_statement(
        self,
        symbol: str,
        statement_type: str,
    ) -> FinancialStatementRecord:
        raise RuntimeError(f"statement failed: {symbol}: {statement_type}")


class FakeWebKnowledgeProvider:
    def search_company_knowledge(
        self,
        *,
        symbol: str,
        theme: str,
        max_records: int = 8,
    ) -> WebKnowledgeResult:
        metadata = make_provider_metadata("stock_news_em")
        return WebKnowledgeResult(
            records=[
                WebKnowledgeRecord(
                    symbol=symbol,
                    title=f"{theme} 主题新闻",
                    summary="公司披露低空经济相关业务进展。",
                    source_name="东方财富新闻",
                    source_type="news",
                    source_url="https://example.test/news",
                    published_at="2026-06-30",
                    retrieved_at="2026-06-30T00:00:00+00:00",
                    provider=metadata,
                    confidence="medium",
                    attributes={"related_theme": theme},
                ),
                WebKnowledgeRecord(
                    symbol=symbol,
                    title="风险提示公告",
                    summary="风险提示：业务推进存在不确定性。",
                    source_name="东方财富公告",
                    source_type="public_disclosure",
                    source_url="https://example.test/notice",
                    published_at="2026-06-29",
                    retrieved_at="2026-06-30T00:00:00+00:00",
                    provider=make_provider_metadata("stock_individual_notice_report"),
                    confidence="high",
                    attributes={"notice_type": "风险提示"},
                ),
            ][:max_records],
            warnings=["web partial warning"],
        )


class FailingWebKnowledgeProvider:
    def search_company_knowledge(
        self,
        *,
        symbol: str,
        theme: str,
        max_records: int = 8,
    ) -> WebKnowledgeResult:
        raise RuntimeError(f"web failed: {symbol}: {theme}")


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
        "financial_statement",
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

    enriched = enrich_recalled_candidate(
        candidate,
        provider=FakeEvidenceProvider(),
        web_knowledge_provider=FakeWebKnowledgeProvider(),
        normalized_query="低空经济",
    )
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
        "financial_statement",
        "text_summary",
        "risk",
        "theme_relationship",
    }.issubset(kinds)
    assert package.missing_kinds == []
    assert provider_source_types == {"market_data_provider"}
    assert any("stock_zyjs_ths" in item.source_name for item in package.evidence)
    assert any("stock_financial_abstract" in item.source_name for item in package.evidence)
    assert any(item.kind == "financial_statement" for item in package.evidence)
    statement_items = [item for item in package.evidence if item.kind == "financial_statement"]
    assert len(statement_items) == 3
    assert all("rows" in item.attributes for item in statement_items)
    assert any(item.source_type == "news" for item in package.evidence)
    assert any(item.source_type == "public_disclosure" for item in package.evidence)
    assert "web partial warning" in package.warnings
    assert WEB_KNOWLEDGE_BOUNDARY not in package.data_boundary


def test_enrich_provider_candidate_records_provider_failures_and_missing_kinds() -> None:
    candidate = make_provider_candidate()

    enriched = enrich_recalled_candidate(candidate, provider=FailingEvidenceProvider())
    package = enriched.evidence_package

    assert package.missing_kinds == [
        "business_summary",
        "financial_summary",
        "financial_statement",
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
    assert any(
        warning.startswith("financial statement unavailable for 300001.SZ")
        for warning in package.warnings
    )


def test_enrich_provider_candidate_records_web_knowledge_failure_without_failing() -> None:
    candidate = make_provider_candidate()

    enriched = enrich_recalled_candidate(
        candidate,
        provider=FakeEvidenceProvider(),
        web_knowledge_provider=FailingWebKnowledgeProvider(),
        normalized_query="低空经济",
    )
    package = enriched.evidence_package

    assert "text_summary" in package.missing_kinds
    assert "risk" in package.missing_kinds
    assert any(
        warning.startswith("web knowledge unavailable for 300001.SZ")
        for warning in package.warnings
    )

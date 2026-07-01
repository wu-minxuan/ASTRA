from astra.theme_research.web_knowledge import AkshareWebKnowledgeProvider


class FakeAkshareWebClient:
    def stock_news_em(self, symbol: str) -> list[dict[str, object]]:
        return [
            {
                "新闻标题": "低空经济业务进展",
                "新闻内容": "公司低空经济业务取得阶段性进展。",
                "发布时间": "2026-06-30 16:31:00",
                "文章来源": "东方财富新闻",
                "新闻链接": "https://example.test/news",
            }
        ]

    def stock_individual_notice_report(
        self,
        security: str,
        symbol: str = "全部",
    ) -> list[dict[str, object]]:
        return [
            {
                "公告标题": "风险提示公告",
                "公告类型": "风险提示",
                "公告日期": "2026-06-29",
                "网址": "https://example.test/notice",
            }
        ]

    def stock_research_report_em(self, symbol: str) -> list[dict[str, object]]:
        return [
            {
                "报告名称": "低空经济专题点评",
                "东财评级": "增持",
                "机构": "示例证券",
                "日期": "2026-06-28",
                "报告PDF链接": "https://example.test/report.pdf",
            }
        ]


class PartiallyFailingAkshareWebClient(FakeAkshareWebClient):
    def stock_news_em(self, symbol: str) -> list[dict[str, object]]:
        raise RuntimeError("news failed")


def test_akshare_web_knowledge_provider_normalizes_records() -> None:
    provider = AkshareWebKnowledgeProvider(
        client=FakeAkshareWebClient(),
        retrieved_at_factory=lambda: "2026-06-30T00:00:00+00:00",
    )

    result = provider.search_company_knowledge(
        symbol="300001.SZ",
        theme="低空经济",
    )

    assert result.warnings == []
    assert [record.source_type for record in result.records] == [
        "news",
        "public_disclosure",
        "research_report",
    ]
    assert result.records[0].published_at == "2026-06-30"
    assert result.records[0].provider.provider_interface == "stock_news_em"
    assert result.records[1].confidence == "high"
    assert result.records[2].source_name == "示例证券"


def test_akshare_web_knowledge_provider_keeps_partial_failure_warning() -> None:
    provider = AkshareWebKnowledgeProvider(
        client=PartiallyFailingAkshareWebClient(),
        retrieved_at_factory=lambda: "2026-06-30T00:00:00+00:00",
    )

    result = provider.search_company_knowledge(
        symbol="300001.SZ",
        theme="低空经济",
    )

    assert len(result.records) == 2
    assert any("stock_news_em" in warning for warning in result.warnings)

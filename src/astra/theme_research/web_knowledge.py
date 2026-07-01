"""Web and document-like knowledge providers for Phase 1 evidence enrichment."""

from __future__ import annotations

from datetime import date, datetime, timezone
from importlib import import_module
from typing import Any, Callable, Protocol

from astra.theme_research.contracts import (
    EvidenceSourceType,
    ProviderMetadata,
    WebKnowledgeRecord,
    WebKnowledgeResult,
)
from astra.theme_research.market_data import (
    AKSHARE_PROVIDER_NAME,
    ProviderDataError,
    provider_stock_code,
)

STOCK_NEWS_INTERFACE = "stock_news_em"
STOCK_NOTICE_INTERFACE = "stock_individual_notice_report"
STOCK_RESEARCH_REPORT_INTERFACE = "stock_research_report_em"
WEB_KNOWLEDGE_PROVIDER_INTERFACES = (
    STOCK_NEWS_INTERFACE,
    STOCK_NOTICE_INTERFACE,
    STOCK_RESEARCH_REPORT_INTERFACE,
)
DEFAULT_MAX_WEB_RECORDS = 8


def _utc_retrieved_at() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class WebKnowledgeUnavailableError(RuntimeError):
    """Raised when a web knowledge provider cannot be called."""


class WebKnowledgeProvider(Protocol):
    """Provider interface for news, disclosure, and research-report evidence."""

    def search_company_knowledge(
        self,
        *,
        symbol: str,
        theme: str,
        max_records: int = DEFAULT_MAX_WEB_RECORDS,
    ) -> WebKnowledgeResult:
        """Return web knowledge records and non-fatal source warnings."""


class AkshareWebKnowledgeProvider:
    """AKShare-backed web knowledge provider with isolated evidence boundaries."""

    def __init__(
        self,
        client: object | None = None,
        retrieved_at_factory: Callable[[], str] = _utc_retrieved_at,
    ) -> None:
        self._client = client
        self._retrieved_at_factory = retrieved_at_factory

    def search_company_knowledge(
        self,
        *,
        symbol: str,
        theme: str,
        max_records: int = DEFAULT_MAX_WEB_RECORDS,
    ) -> WebKnowledgeResult:
        """Fetch recent AKShare news, notices, and research-report records."""
        raw_symbol = provider_stock_code(symbol)
        warnings: list[str] = []
        records: list[WebKnowledgeRecord] = []
        for provider_interface, loader in (
            (STOCK_NEWS_INTERFACE, self._news_records),
            (STOCK_NOTICE_INTERFACE, self._notice_records),
            (STOCK_RESEARCH_REPORT_INTERFACE, self._research_report_records),
        ):
            try:
                records.extend(loader(raw_symbol, symbol, theme))
            except Exception as exc:
                warnings.append(
                    f"web knowledge source unavailable for {symbol}: "
                    f"{provider_interface}: {type(exc).__name__}: {exc}"
                )
        return WebKnowledgeResult(
            records=_deduplicate_records(records)[:max_records],
            warnings=warnings,
        )

    def _news_records(
        self,
        raw_symbol: str,
        symbol: str,
        theme: str,
    ) -> list[WebKnowledgeRecord]:
        metadata = self._metadata(STOCK_NEWS_INTERFACE)
        rows = _iter_rows(self._call(STOCK_NEWS_INTERFACE, symbol=raw_symbol))
        records = [
            _news_record_from_row(row, symbol, theme, metadata)
            for row in rows
            if _optional_value(row, ("新闻标题", "title", "标题")) is not None
        ]
        if not records:
            raise WebKnowledgeUnavailableError("AKShare news interface returned no records")
        return records

    def _notice_records(
        self,
        raw_symbol: str,
        symbol: str,
        theme: str,
    ) -> list[WebKnowledgeRecord]:
        metadata = self._metadata(STOCK_NOTICE_INTERFACE)
        rows = _iter_rows(
            self._call(STOCK_NOTICE_INTERFACE, security=raw_symbol, symbol="全部")
        )
        records = [
            _notice_record_from_row(row, symbol, theme, metadata)
            for row in rows
            if _optional_value(row, ("公告标题", "title", "标题")) is not None
        ]
        if not records:
            raise WebKnowledgeUnavailableError("AKShare notice interface returned no records")
        return records

    def _research_report_records(
        self,
        raw_symbol: str,
        symbol: str,
        theme: str,
    ) -> list[WebKnowledgeRecord]:
        metadata = self._metadata(STOCK_RESEARCH_REPORT_INTERFACE)
        rows = _iter_rows(self._call(STOCK_RESEARCH_REPORT_INTERFACE, symbol=raw_symbol))
        records = [
            _research_report_record_from_row(row, symbol, theme, metadata)
            for row in rows
            if _optional_value(row, ("报告名称", "title", "标题")) is not None
        ]
        if not records:
            raise WebKnowledgeUnavailableError(
                "AKShare research-report interface returned no records"
            )
        return records

    def _metadata(self, provider_interface: str) -> ProviderMetadata:
        return ProviderMetadata(
            provider_name=AKSHARE_PROVIDER_NAME,
            provider_interface=provider_interface,
            retrieved_at=self._retrieved_at_factory(),
        )

    def _call(self, function_name: str, **kwargs: object) -> object:
        client = self._load_client()
        function = getattr(client, function_name, None)
        if function is None:
            raise WebKnowledgeUnavailableError(
                f"AKShare function not available: {function_name}"
            )
        try:
            return function(**kwargs)
        except Exception as exc:
            raise WebKnowledgeUnavailableError(
                f"AKShare call failed: {function_name}: {type(exc).__name__}: {exc}"
            ) from exc

    def _load_client(self) -> object:
        if self._client is None:
            self._client = import_module("akshare")
        return self._client


def _news_record_from_row(
    row: dict[str, object],
    symbol: str,
    theme: str,
    metadata: ProviderMetadata,
) -> WebKnowledgeRecord:
    title = _required_value(row, ("新闻标题", "title", "标题"))
    source_name = _optional_value(row, ("文章来源", "source", "来源")) or "东方财富新闻"
    published_at = _contract_date(_optional_value(row, ("发布时间", "time", "日期")))
    summary = _optional_value(row, ("新闻内容", "content", "摘要")) or title
    return _record(
        symbol=symbol,
        title=title,
        summary=summary,
        source_name=source_name,
        source_type="news",
        source_url=_optional_value(row, ("新闻链接", "url", "链接")),
        published_at=published_at,
        theme=theme,
        metadata=metadata,
        confidence="medium",
        attributes=_jsonable_row(row),
    )


def _notice_record_from_row(
    row: dict[str, object],
    symbol: str,
    theme: str,
    metadata: ProviderMetadata,
) -> WebKnowledgeRecord:
    title = _required_value(row, ("公告标题", "title", "标题"))
    notice_type = _optional_value(row, ("公告类型", "type", "类型"))
    source_name = "东方财富公告"
    published_at = _contract_date(_optional_value(row, ("公告日期", "date", "日期")))
    summary = f"{notice_type}：{title}" if notice_type else title
    return _record(
        symbol=symbol,
        title=title,
        summary=summary,
        source_name=source_name,
        source_type="public_disclosure",
        source_url=_optional_value(row, ("网址", "url", "链接")),
        published_at=published_at,
        theme=theme,
        metadata=metadata,
        confidence="high",
        attributes=_jsonable_row(row),
    )


def _research_report_record_from_row(
    row: dict[str, object],
    symbol: str,
    theme: str,
    metadata: ProviderMetadata,
) -> WebKnowledgeRecord:
    title = _required_value(row, ("报告名称", "title", "标题"))
    institution = _optional_value(row, ("机构", "source", "来源"))
    rating = _optional_value(row, ("东财评级", "评级", "rating"))
    published_at = _contract_date(_optional_value(row, ("日期", "date")))
    summary_parts = [title]
    if institution:
        summary_parts.append(f"机构：{institution}")
    if rating:
        summary_parts.append(f"评级：{rating}")
    return _record(
        symbol=symbol,
        title=title,
        summary="；".join(summary_parts),
        source_name=institution or "东方财富研报",
        source_type="research_report",
        source_url=_optional_value(row, ("报告PDF链接", "url", "链接")),
        published_at=published_at,
        theme=theme,
        metadata=metadata,
        confidence="medium",
        attributes=_jsonable_row(row),
    )


def _record(
    *,
    symbol: str,
    title: str,
    summary: str,
    source_name: str,
    source_type: EvidenceSourceType,
    source_url: str | None,
    published_at: str | None,
    theme: str,
    metadata: ProviderMetadata,
    confidence: str,
    attributes: dict[str, Any],
) -> WebKnowledgeRecord:
    return WebKnowledgeRecord(
        symbol=symbol,
        title=title,
        summary=summary,
        source_name=source_name,
        source_type=source_type,
        source_url=source_url,
        published_at=published_at,
        retrieved_at=metadata.retrieved_at,
        provider=metadata,
        confidence=confidence,
        attributes={
            **attributes,
            "related_theme": theme,
            "provider_interface": metadata.provider_interface,
        },
    )


def _deduplicate_records(records: list[WebKnowledgeRecord]) -> list[WebKnowledgeRecord]:
    deduplicated: list[WebKnowledgeRecord] = []
    seen: set[tuple[str, str, str | None]] = set()
    for record in records:
        key = (record.source_type, record.title, record.source_url)
        if key not in seen:
            deduplicated.append(record)
            seen.add(key)
    return deduplicated


def _iter_rows(tabular_data: object) -> list[dict[str, object]]:
    if hasattr(tabular_data, "to_dict"):
        records = tabular_data.to_dict("records")
    else:
        records = tabular_data
    if not isinstance(records, list):
        raise ProviderDataError("web knowledge provider response is not tabular")
    rows: list[dict[str, object]] = []
    for record in records:
        if not isinstance(record, dict):
            raise ProviderDataError("web knowledge provider row is not a mapping")
        rows.append(record)
    return rows


def _required_value(row: dict[str, object], keys: tuple[str, ...]) -> str:
    value = _optional_value(row, keys)
    if value is None:
        raise ProviderDataError(f"web knowledge row missing required fields: {keys}")
    return value


def _optional_value(row: dict[str, object], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = row.get(key)
        if value is not None and str(value).strip() and str(value).lower() != "nan":
            return str(value).strip()
    return None


def _contract_date(value: str | None) -> str | None:
    if not value:
        return None
    if len(value) >= 10:
        candidate = value[:10]
        if _is_contract_date(candidate):
            return candidate
    return None


def _is_contract_date(value: str) -> bool:
    parts = value.split("-")
    return (
        len(parts) == 3
        and len(parts[0]) == 4
        and len(parts[1]) == 2
        and len(parts[2]) == 2
        and all(part.isdigit() for part in parts)
    )


def _jsonable_row(row: dict[str, object]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, value in row.items():
        jsonable = _jsonable_value(value)
        if jsonable is not None:
            output[str(key)] = jsonable
    return output


def _jsonable_value(value: object) -> Any:
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, float) and value != value:
        return None
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    text = str(value)
    if text.lower() in {"nan", "nat", "none"}:
        return None
    return value

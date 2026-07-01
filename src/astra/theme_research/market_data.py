"""Market data provider and adapter layer for Phase 1 theme research."""

from __future__ import annotations

from datetime import date, datetime, timezone
from importlib import import_module
from typing import Any, Callable, Protocol

from astra.theme_research.contracts import (
    BusinessProfileRecord,
    ConceptBoardRecord,
    ConceptConstituentRecord,
    FinancialSnapshotRecord,
    FinancialStatementRecord,
    FinancialStatementType,
    FixtureCompany,
    FixtureThemeDataset,
    MarketDataCompany,
    ProviderMetadata,
    StockSourceRecord,
)

AKSHARE_PROVIDER_NAME = "akshare"
FIXTURE_PROVIDER_NAME = "fixture"
STOCK_BASIC_INTERFACE = "stock_info_a_code_name"
CONCEPT_BOARDS_INTERFACE = "stock_board_concept_name_em"
CONCEPT_CONSTITUENTS_INTERFACE = "stock_board_concept_cons_em"
BUSINESS_PROFILE_INTERFACE = "stock_zyjs_ths"
FINANCIAL_ABSTRACT_INTERFACE = "stock_financial_abstract"
BALANCE_SHEET_INTERFACE = "stock_balance_sheet_by_report_em"
INCOME_STATEMENT_INTERFACE = "stock_profit_sheet_by_report_em"
CASH_FLOW_STATEMENT_INTERFACE = "stock_cash_flow_sheet_by_report_em"
FIXTURE_INTERFACE = "load_low_altitude_economy_fixture"
FINANCIAL_METRIC_NAMES = (
    "营业总收入",
    "归母净利润",
    "净利润",
    "扣非净利润",
)
FINANCIAL_STATEMENT_INTERFACES: dict[FinancialStatementType, str] = {
    "balance_sheet": BALANCE_SHEET_INTERFACE,
    "income_statement": INCOME_STATEMENT_INTERFACE,
    "cash_flow_statement": CASH_FLOW_STATEMENT_INTERFACE,
}


def _utc_retrieved_at() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class ProviderDataError(RuntimeError):
    """Raised when provider data cannot be normalized into ASTRA records."""


class ProviderUnavailableError(ProviderDataError):
    """Raised when a provider cannot be called or returns no usable data."""


class MarketDataProvider(Protocol):
    """Provider interface for normalized market data source records."""

    def list_stock_source_records(self) -> list[StockSourceRecord]:
        """Return normalized A-share stock records from the provider."""

    def list_concept_boards(self) -> list[ConceptBoardRecord]:
        """Return normalized concept board records from the provider."""

    def list_concept_constituents(
        self,
        concept_name: str,
    ) -> list[ConceptConstituentRecord]:
        """Return normalized constituent records for a concept or board."""

    def get_business_profile(self, symbol: str) -> BusinessProfileRecord:
        """Return a normalized business profile record for one stock."""

    def get_financial_snapshot(self, symbol: str) -> FinancialSnapshotRecord:
        """Return a normalized financial snapshot record for one stock."""

    def get_financial_statement(
        self,
        symbol: str,
        statement_type: FinancialStatementType,
    ) -> FinancialStatementRecord:
        """Return one full financial statement table for one stock."""


class AkshareMarketDataProvider:
    """AKShare-backed market data provider with lazy client import."""

    def __init__(
        self,
        client: object | None = None,
        retrieved_at_factory: Callable[[], str] = _utc_retrieved_at,
    ) -> None:
        self._client = client
        self._retrieved_at_factory = retrieved_at_factory

    def list_stock_source_records(self) -> list[StockSourceRecord]:
        metadata = self._metadata(STOCK_BASIC_INTERFACE)
        rows = _iter_rows(self._call(STOCK_BASIC_INTERFACE))
        records: list[StockSourceRecord] = []
        for row in rows:
            if not _has_any(row, ("code", "代码", "股票代码", "证券代码")):
                continue
            try:
                records.append(stock_source_record_from_row(row, metadata))
            except ProviderDataError:
                continue
        if not records:
            raise ProviderUnavailableError("AKShare stock basic interface returned no records")
        return records

    def list_concept_boards(self) -> list[ConceptBoardRecord]:
        metadata = self._metadata(CONCEPT_BOARDS_INTERFACE)
        rows = _iter_rows(self._call(CONCEPT_BOARDS_INTERFACE))
        records: list[ConceptBoardRecord] = []
        for row in rows:
            if not _has_any(row, ("name", "名称", "板块名称", "概念名称")):
                continue
            try:
                records.append(concept_board_record_from_row(row, metadata))
            except ProviderDataError:
                continue
        if not records:
            raise ProviderUnavailableError("AKShare concept board interface returned no records")
        return records

    def list_concept_constituents(
        self,
        concept_name: str,
    ) -> list[ConceptConstituentRecord]:
        if not concept_name.strip():
            raise ProviderDataError("concept_name must not be empty")

        metadata = self._metadata(CONCEPT_CONSTITUENTS_INTERFACE)
        rows = _iter_rows(
            self._call(CONCEPT_CONSTITUENTS_INTERFACE, symbol=concept_name.strip())
        )
        records: list[ConceptConstituentRecord] = []
        for row in rows:
            if not _has_any(row, ("code", "代码", "股票代码", "证券代码")):
                continue
            try:
                records.append(
                    concept_constituent_record_from_row(row, concept_name.strip(), metadata)
                )
            except ProviderDataError:
                continue
        if not records:
            raise ProviderUnavailableError(
                f"AKShare concept interface returned no records for {concept_name}"
            )
        return records

    def get_business_profile(self, symbol: str) -> BusinessProfileRecord:
        raw_symbol = provider_stock_code(symbol)
        metadata = self._metadata(BUSINESS_PROFILE_INTERFACE)
        rows = _iter_rows(self._call(BUSINESS_PROFILE_INTERFACE, symbol=raw_symbol))
        for row in rows:
            try:
                return business_profile_record_from_row(row, raw_symbol, metadata)
            except ProviderDataError:
                continue
        raise ProviderUnavailableError(
            f"AKShare business profile interface returned no records for {symbol}"
        )

    def get_financial_snapshot(self, symbol: str) -> FinancialSnapshotRecord:
        raw_symbol = provider_stock_code(symbol)
        metadata = self._metadata(FINANCIAL_ABSTRACT_INTERFACE)
        rows = _iter_rows(self._call(FINANCIAL_ABSTRACT_INTERFACE, symbol=raw_symbol))
        return financial_snapshot_record_from_rows(rows, raw_symbol, metadata)

    def get_financial_statement(
        self,
        symbol: str,
        statement_type: FinancialStatementType,
    ) -> FinancialStatementRecord:
        raw_symbol = provider_stock_code(symbol)
        provider_symbol = provider_market_symbol(symbol)
        provider_interface = FINANCIAL_STATEMENT_INTERFACES[statement_type]
        metadata = self._metadata(provider_interface)
        rows = _iter_rows(self._call(provider_interface, symbol=provider_symbol))
        return financial_statement_record_from_rows(
            rows,
            raw_symbol,
            statement_type,
            metadata,
        )

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
            raise ProviderUnavailableError(f"AKShare function not available: {function_name}")
        try:
            return function(**kwargs)
        except Exception as exc:  # pragma: no cover - exercised through fallback tests.
            message = f"AKShare call failed: {function_name}: {type(exc).__name__}: {exc}"
            raise ProviderUnavailableError(
                message
            ) from exc

    def _load_client(self) -> object:
        if self._client is None:
            self._client = import_module("akshare")
        return self._client


class FixtureMarketDataProvider:
    """Fixture-backed provider used for tests and primary-provider fallback."""

    def __init__(self, dataset: FixtureThemeDataset) -> None:
        self._dataset = dataset

    def list_stock_source_records(self) -> list[StockSourceRecord]:
        return [
            stock_source_record_from_fixture_company(
                company,
                self._metadata(FIXTURE_INTERFACE),
            )
            for company in self._dataset.companies
        ]

    def list_concept_boards(self) -> list[ConceptBoardRecord]:
        names = [self._dataset.display_name, *self._dataset.aliases]
        records: list[ConceptBoardRecord] = []
        seen: set[str] = set()
        for name in names:
            normalized_name = _normalize_provider_term(name)
            if not normalized_name or normalized_name in seen:
                continue
            seen.add(normalized_name)
            records.append(
                ConceptBoardRecord(
                    raw_name=name,
                    concept_name=name,
                    provider=self._metadata(FIXTURE_INTERFACE),
                )
            )
        return records

    def list_concept_constituents(
        self,
        concept_name: str,
    ) -> list[ConceptConstituentRecord]:
        companies = self._companies_for_concept(concept_name)
        return [
            concept_constituent_record_from_fixture_company(
                company,
                concept_name.strip() or self._dataset.display_name,
                self._metadata(FIXTURE_INTERFACE),
            )
            for company in companies
        ]

    def get_business_profile(self, symbol: str) -> BusinessProfileRecord:
        company = self._company_by_symbol(symbol)
        return BusinessProfileRecord(
            raw_symbol=company.symbol,
            symbol=company.symbol,
            main_business=company.business_summary,
            business_scope=company.text_summary,
            provider=self._metadata(FIXTURE_INTERFACE),
        )

    def get_financial_snapshot(self, symbol: str) -> FinancialSnapshotRecord:
        company = self._company_by_symbol(symbol)
        return FinancialSnapshotRecord(
            raw_symbol=company.symbol,
            symbol=company.symbol,
            report_period=self._dataset.as_of,
            metrics={"fixture_financial_summary": company.financial_summary},
            provider=self._metadata(FIXTURE_INTERFACE),
        )

    def get_financial_statement(
        self,
        symbol: str,
        statement_type: FinancialStatementType,
    ) -> FinancialStatementRecord:
        company = self._company_by_symbol(symbol)
        return FinancialStatementRecord(
            raw_symbol=company.symbol,
            symbol=company.symbol,
            statement_type=statement_type,
            columns=["REPORT_DATE", "FIXTURE_FINANCIAL_SUMMARY"],
            rows=[
                {
                    "REPORT_DATE": self._dataset.as_of,
                    "FIXTURE_FINANCIAL_SUMMARY": company.financial_summary,
                }
            ],
            provider=self._metadata(FIXTURE_INTERFACE),
        )

    def _metadata(self, provider_interface: str) -> ProviderMetadata:
        return ProviderMetadata(
            provider_name=FIXTURE_PROVIDER_NAME,
            provider_interface=provider_interface,
            retrieved_at=self._dataset.as_of,
            is_fallback=True,
        )

    def _companies_for_concept(self, concept_name: str) -> list[FixtureCompany]:
        normalized_concept = _normalize_provider_term(concept_name)
        if not normalized_concept:
            return []

        theme_terms = {
            _normalize_provider_term(self._dataset.display_name),
            *(_normalize_provider_term(alias) for alias in self._dataset.aliases),
        }
        if normalized_concept in theme_terms:
            return list(self._dataset.companies)

        return [
            company
            for company in self._dataset.companies
            if normalized_concept
            in {_normalize_provider_term(concept) for concept in company.concepts}
        ]

    def _company_by_symbol(self, symbol: str) -> FixtureCompany:
        normalized_symbol = symbol.strip().upper()
        for company in self._dataset.companies:
            if company.symbol == normalized_symbol:
                return company
        raise ProviderUnavailableError(f"fixture company not found: {symbol}")


class FallbackMarketDataProvider:
    """Market data provider that falls back to fixture records on failure."""

    def __init__(
        self,
        primary: MarketDataProvider,
        fallback: MarketDataProvider,
    ) -> None:
        self._primary = primary
        self._fallback = fallback

    def list_stock_source_records(self) -> list[StockSourceRecord]:
        try:
            records = self._primary.list_stock_source_records()
            if records:
                return records
            failure_reason = "primary provider returned no stock records"
        except Exception as exc:
            failure_reason = str(exc)
        return [
            _with_failure_reason(record, failure_reason)
            for record in self._fallback.list_stock_source_records()
        ]

    def list_concept_boards(self) -> list[ConceptBoardRecord]:
        try:
            records = self._primary.list_concept_boards()
            if records:
                return records
            failure_reason = "primary provider returned no concept boards"
        except Exception as exc:
            failure_reason = str(exc)
        return [
            _with_failure_reason(record, failure_reason)
            for record in self._fallback.list_concept_boards()
        ]

    def list_concept_constituents(
        self,
        concept_name: str,
    ) -> list[ConceptConstituentRecord]:
        try:
            records = self._primary.list_concept_constituents(concept_name)
            if records:
                return records
            failure_reason = "primary provider returned no concept constituents"
        except Exception as exc:
            failure_reason = str(exc)
        return [
            _with_failure_reason(record, failure_reason)
            for record in self._fallback.list_concept_constituents(concept_name)
        ]

    def get_business_profile(self, symbol: str) -> BusinessProfileRecord:
        try:
            return self._primary.get_business_profile(symbol)
        except Exception as exc:
            failure_reason = str(exc)
        return _with_failure_reason(
            self._fallback.get_business_profile(symbol),
            failure_reason,
        )

    def get_financial_snapshot(self, symbol: str) -> FinancialSnapshotRecord:
        try:
            return self._primary.get_financial_snapshot(symbol)
        except Exception as exc:
            failure_reason = str(exc)
        return _with_failure_reason(
            self._fallback.get_financial_snapshot(symbol),
            failure_reason,
        )

    def get_financial_statement(
        self,
        symbol: str,
        statement_type: FinancialStatementType,
    ) -> FinancialStatementRecord:
        try:
            return self._primary.get_financial_statement(symbol, statement_type)
        except Exception as exc:
            failure_reason = str(exc)
        return _with_failure_reason(
            self._fallback.get_financial_statement(symbol, statement_type),
            failure_reason,
        )


def concept_board_record_from_row(
    row: dict[str, object],
    metadata: ProviderMetadata,
) -> ConceptBoardRecord:
    """Normalize one provider row into a concept board record."""
    name = _required_value(row, ("name", "名称", "板块名称", "概念名称"))
    return ConceptBoardRecord(
        raw_name=name,
        concept_name=name,
        board_code=_optional_value(row, ("code", "代码", "板块代码", "概念代码")),
        provider=metadata,
    )


def stock_source_record_from_row(
    row: dict[str, object],
    metadata: ProviderMetadata,
) -> StockSourceRecord:
    """Normalize one provider row into a stock source record."""
    raw_symbol = _required_value(row, ("code", "代码", "股票代码", "证券代码"))
    symbol = normalize_a_share_symbol(raw_symbol)
    return StockSourceRecord(
        raw_symbol=raw_symbol,
        symbol=symbol,
        name=_required_value(row, ("name", "名称", "股票简称", "证券简称")),
        exchange=exchange_from_symbol(symbol),
        industry=_optional_value(row, ("industry", "行业", "所属行业")),
        listing_status=_optional_value(row, ("listing_status", "上市状态")),
        provider=metadata,
    )


def concept_constituent_record_from_row(
    row: dict[str, object],
    concept_name: str,
    metadata: ProviderMetadata,
) -> ConceptConstituentRecord:
    """Normalize one provider row into a concept constituent record."""
    raw_symbol = _required_value(row, ("code", "代码", "股票代码", "证券代码"))
    symbol = normalize_a_share_symbol(raw_symbol)
    return ConceptConstituentRecord(
        concept_name=concept_name,
        raw_symbol=raw_symbol,
        symbol=symbol,
        name=_required_value(row, ("name", "名称", "股票简称", "证券简称")),
        exchange=exchange_from_symbol(symbol),
        industry=_optional_value(row, ("industry", "行业", "所属行业")),
        provider=metadata,
    )


def business_profile_record_from_row(
    row: dict[str, object],
    raw_symbol: str,
    metadata: ProviderMetadata,
) -> BusinessProfileRecord:
    """Normalize one provider row into a business profile record."""
    row_symbol = _optional_value(row, ("code", "代码", "股票代码")) or raw_symbol
    symbol = normalize_a_share_symbol(row_symbol)
    main_business = _optional_value(row, ("main_business", "主营业务"))
    product_type = _optional_value(row, ("product_type", "产品类型"))
    product_name = _optional_value(row, ("product_name", "产品名称"))
    business_scope = _optional_value(row, ("business_scope", "经营范围"))
    if not any((main_business, product_type, product_name, business_scope)):
        raise ProviderDataError("provider business profile row contains no usable fields")
    return BusinessProfileRecord(
        raw_symbol=raw_symbol,
        symbol=symbol,
        main_business=main_business,
        product_type=product_type,
        product_name=product_name,
        business_scope=business_scope,
        provider=metadata,
    )


def financial_snapshot_record_from_rows(
    rows: list[dict[str, object]],
    raw_symbol: str,
    metadata: ProviderMetadata,
) -> FinancialSnapshotRecord:
    """Normalize provider financial abstract rows into one latest snapshot."""
    symbol = normalize_a_share_symbol(raw_symbol)
    report_periods = sorted(
        {
            key
            for row in rows
            for key in row
            if _is_report_period(key)
        },
        reverse=True,
    )
    for report_period in report_periods:
        metrics = _financial_metrics_for_period(rows, report_period)
        if metrics:
            return FinancialSnapshotRecord(
                raw_symbol=raw_symbol,
                symbol=symbol,
                report_period=report_period,
                metrics=metrics,
                provider=metadata,
            )
    raise ProviderUnavailableError(
        f"provider financial abstract returned no usable metrics for {raw_symbol}"
    )


def financial_statement_record_from_rows(
    rows: list[dict[str, object]],
    raw_symbol: str,
    statement_type: FinancialStatementType,
    metadata: ProviderMetadata,
) -> FinancialStatementRecord:
    """Normalize one provider financial statement table without dropping fields."""
    symbol = normalize_a_share_symbol(raw_symbol)
    normalized_rows = [_jsonable_row(row) for row in rows]
    normalized_rows = [row for row in normalized_rows if row]
    if not normalized_rows:
        raise ProviderUnavailableError(
            f"provider {statement_type} returned no usable rows for {raw_symbol}"
        )
    return FinancialStatementRecord(
        raw_symbol=raw_symbol,
        symbol=symbol,
        statement_type=statement_type,
        columns=_statement_columns(normalized_rows),
        rows=normalized_rows,
        provider=metadata,
    )


def stock_source_record_from_fixture_company(
    company: FixtureCompany,
    metadata: ProviderMetadata,
) -> StockSourceRecord:
    """Convert a fixture company into a provider source record."""
    return StockSourceRecord(
        raw_symbol=company.symbol,
        symbol=company.symbol,
        name=company.name,
        exchange=company.exchange,
        industry=company.industry,
        listing_status="fixture_active",
        provider=metadata,
    )


def concept_constituent_record_from_fixture_company(
    company: FixtureCompany,
    concept_name: str,
    metadata: ProviderMetadata,
) -> ConceptConstituentRecord:
    """Convert a fixture company into a concept constituent source record."""
    return ConceptConstituentRecord(
        concept_name=concept_name,
        raw_symbol=company.symbol,
        symbol=company.symbol,
        name=company.name,
        exchange=company.exchange,
        industry=company.industry,
        provider=metadata,
    )


def market_data_company_from_stock_record(record: StockSourceRecord) -> MarketDataCompany:
    """Adapt a provider stock record into an internal market data company."""
    return MarketDataCompany(
        symbol=record.symbol,
        name=record.name,
        exchange=record.exchange,
        industry=record.industry,
        provider=record.provider,
    )


def market_data_company_from_concept_record(
    record: ConceptConstituentRecord,
) -> MarketDataCompany:
    """Adapt a concept constituent record into an internal market data company."""
    return MarketDataCompany(
        symbol=record.symbol,
        name=record.name,
        exchange=record.exchange,
        industry=record.industry,
        concepts=[record.concept_name],
        provider=record.provider,
    )


def normalize_a_share_symbol(raw_symbol: object) -> str:
    """Normalize supported A-share symbols to ASTRA's 000000.SZ/SH format."""
    value = str(raw_symbol).strip().upper()
    if not value:
        raise ProviderDataError("stock symbol is empty")

    if value.endswith((".SZ", ".SH")) and len(value) == 9:
        code = value[:6]
    elif value.startswith(("SZ", "SH")) and len(value) == 8:
        code = value[2:]
    else:
        code = "".join(character for character in value if character.isdigit())

    if len(code) != 6:
        raise ProviderDataError(f"unsupported stock symbol: {raw_symbol}")
    if code.startswith("6"):
        return f"{code}.SH"
    if code.startswith(("0", "3")):
        return f"{code}.SZ"
    raise ProviderDataError(f"unsupported Phase 1 stock exchange for symbol: {raw_symbol}")


def provider_stock_code(symbol: str) -> str:
    """Convert a supported ASTRA symbol to the provider's six-digit stock code."""
    return normalize_a_share_symbol(symbol)[:6]


def provider_market_symbol(symbol: str) -> str:
    """Convert an ASTRA symbol to AKShare's market-prefixed code."""
    normalized = normalize_a_share_symbol(symbol)
    code = normalized[:6]
    if normalized.endswith(".SZ"):
        return f"SZ{code}"
    if normalized.endswith(".SH"):
        return f"SH{code}"
    raise ProviderDataError(f"unsupported Phase 1 exchange for symbol: {symbol}")


def exchange_from_symbol(symbol: str) -> str:
    """Infer Phase 1 exchange code from a normalized A-share symbol."""
    if symbol.endswith(".SH"):
        return "SSE"
    if symbol.endswith(".SZ"):
        return "SZSE"
    raise ProviderDataError(f"unsupported Phase 1 exchange for symbol: {symbol}")


def _normalize_provider_term(value: str) -> str:
    return value.strip().casefold()


def _iter_rows(tabular_data: object) -> list[dict[str, object]]:
    if hasattr(tabular_data, "to_dict"):
        records = tabular_data.to_dict("records")
    else:
        records = tabular_data

    if not isinstance(records, list):
        raise ProviderDataError("provider response is not tabular")

    rows: list[dict[str, object]] = []
    for record in records:
        if not isinstance(record, dict):
            raise ProviderDataError("provider row is not a mapping")
        rows.append(record)
    return rows


def _required_value(row: dict[str, object], keys: tuple[str, ...]) -> str:
    value = _optional_value(row, keys)
    if value is None:
        raise ProviderDataError(f"provider row missing required fields: {', '.join(keys)}")
    return value


def _optional_value(row: dict[str, object], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = row.get(key)
        if value is not None and str(value).strip() and str(value).lower() != "nan":
            return str(value).strip()
    return None


def _is_report_period(key: object) -> bool:
    value = str(key)
    return len(value) == 8 and value.isdigit()


def _financial_metrics_for_period(
    rows: list[dict[str, object]],
    report_period: str,
) -> dict[str, str]:
    metrics: dict[str, str] = {}
    for row in rows:
        metric_name = _optional_value(row, ("指标", "metric", "指标名称"))
        if metric_name not in FINANCIAL_METRIC_NAMES:
            continue
        metric_value = _optional_value(row, (report_period,))
        if metric_value is not None:
            metrics[metric_name] = metric_value
    return metrics


def _has_any(row: dict[str, object], keys: tuple[str, ...]) -> bool:
    return _optional_value(row, keys) is not None


def _with_failure_reason(record: Any, failure_reason: str) -> Any:
    provider = record.provider.model_copy(
        update={
            "is_fallback": True,
            "failure_reason": failure_reason,
        }
    )
    return record.model_copy(update={"provider": provider})


def _statement_columns(rows: list[dict[str, Any]]) -> list[str]:
    columns: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                columns.append(key)
                seen.add(key)
    return columns


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

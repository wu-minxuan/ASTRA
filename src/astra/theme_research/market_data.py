"""Market data provider and adapter layer for Phase 1 theme research."""

from __future__ import annotations

from datetime import datetime, timezone
from importlib import import_module
from typing import Any, Callable, Protocol

from astra.theme_research.contracts import (
    ConceptConstituentRecord,
    FixtureCompany,
    FixtureThemeDataset,
    MarketDataCompany,
    ProviderMetadata,
    StockSourceRecord,
)
from astra.theme_research.recall import normalize_theme_query

AKSHARE_PROVIDER_NAME = "akshare"
FIXTURE_PROVIDER_NAME = "fixture"
STOCK_BASIC_INTERFACE = "stock_info_a_code_name"
CONCEPT_CONSTITUENTS_INTERFACE = "stock_board_concept_cons_em"
FIXTURE_INTERFACE = "load_low_altitude_economy_fixture"


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

    def list_concept_constituents(
        self,
        concept_name: str,
    ) -> list[ConceptConstituentRecord]:
        """Return normalized constituent records for a concept or board."""


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
            raise ProviderUnavailableError(f"AKShare call failed: {function_name}") from exc

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

    def _metadata(self, provider_interface: str) -> ProviderMetadata:
        return ProviderMetadata(
            provider_name=FIXTURE_PROVIDER_NAME,
            provider_interface=provider_interface,
            retrieved_at=self._dataset.as_of,
            is_fallback=True,
        )

    def _companies_for_concept(self, concept_name: str) -> list[FixtureCompany]:
        normalized_concept = normalize_theme_query(concept_name)
        if not normalized_concept:
            return []

        theme_terms = {
            normalize_theme_query(self._dataset.display_name),
            *(normalize_theme_query(alias) for alias in self._dataset.aliases),
        }
        if normalized_concept in theme_terms:
            return list(self._dataset.companies)

        return [
            company
            for company in self._dataset.companies
            if normalized_concept
            in {normalize_theme_query(concept) for concept in company.concepts}
        ]


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


def exchange_from_symbol(symbol: str) -> str:
    """Infer Phase 1 exchange code from a normalized A-share symbol."""
    if symbol.endswith(".SH"):
        return "SSE"
    if symbol.endswith(".SZ"):
        return "SZSE"
    raise ProviderDataError(f"unsupported Phase 1 exchange for symbol: {symbol}")


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

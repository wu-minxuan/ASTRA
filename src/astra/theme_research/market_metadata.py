"""Market metadata cache for Phase 1 provider-backed recall."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import Field

from astra.theme_research.contracts import (
    BusinessProfileRecord,
    ConceptBoardRecord,
    ConceptConstituentRecord,
    ContractModel,
    Exchange,
    FinancialSnapshotRecord,
    ProviderMetadata,
    StockSourceRecord,
)
from astra.theme_research.market_data import (
    CONCEPT_CONSTITUENTS_INTERFACE,
    MarketDataProvider,
    ProviderUnavailableError,
    normalize_a_share_symbol,
)
from astra.theme_research.recall import normalize_theme_query

DEFAULT_MARKET_METADATA_PATH = (
    Path(__file__).resolve().parent / "metadata" / "market_metadata.seed.json"
)
MARKET_METADATA_CACHE_INTERFACE = "market_metadata_cache"


class CachedConceptConstituent(ContractModel):
    """One cached concept constituent sourced from market metadata snapshots."""

    raw_symbol: str
    symbol: str
    name: str
    exchange: Exchange
    industry: str | None = None


class CachedConceptBoard(ContractModel):
    """Cached concept-board mapping and optional constituent snapshot."""

    canonical_name: str
    aliases: list[str]
    provider_name: Literal["akshare"]
    provider_interface: str
    board_code: str
    provider_board_name: str
    retrieved_at: str
    constituents: list[CachedConceptConstituent] = Field(default_factory=list)


class MarketMetadataSnapshot(ContractModel):
    """File-backed market metadata snapshot."""

    snapshot_id: str
    as_of: str
    description: str
    concept_boards: list[CachedConceptBoard]


class MarketMetadataStore:
    """Read-only file-backed market metadata store."""

    def __init__(self, snapshot: MarketMetadataSnapshot) -> None:
        self._snapshot = snapshot

    @classmethod
    def load(cls, path: Path = DEFAULT_MARKET_METADATA_PATH) -> MarketMetadataStore:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return cls(MarketMetadataSnapshot.model_validate(payload))

    @property
    def snapshot(self) -> MarketMetadataSnapshot:
        return self._snapshot

    def list_concept_boards(self) -> list[ConceptBoardRecord]:
        records: list[ConceptBoardRecord] = []
        for board in self._snapshot.concept_boards:
            records.append(self._concept_board_record(board, board.canonical_name))
            for alias in board.aliases:
                if normalize_theme_query(alias) == normalize_theme_query(board.canonical_name):
                    continue
                records.append(self._concept_board_record(board, alias))
        return records

    def find_concept_board(self, concept_name: str) -> CachedConceptBoard | None:
        normalized_name = normalize_theme_query(concept_name)
        if not normalized_name:
            return None
        for board in self._snapshot.concept_boards:
            normalized_terms = {
                normalize_theme_query(board.canonical_name),
                normalize_theme_query(board.provider_board_name),
                normalize_theme_query(board.board_code),
                *(normalize_theme_query(alias) for alias in board.aliases),
            }
            if normalized_name in normalized_terms:
                return board
        return None

    def list_concept_constituents(
        self,
        concept_name: str,
        *,
        failure_reason: str | None = None,
    ) -> list[ConceptConstituentRecord]:
        board = self.find_concept_board(concept_name)
        if board is None:
            return []
        return [
            ConceptConstituentRecord(
                concept_name=board.canonical_name,
                raw_symbol=constituent.raw_symbol,
                symbol=normalize_a_share_symbol(constituent.symbol),
                name=constituent.name,
                exchange=constituent.exchange,
                industry=constituent.industry,
                provider=self._metadata(
                    board,
                    provider_interface=f"{MARKET_METADATA_CACHE_INTERFACE}:"
                    f"{CONCEPT_CONSTITUENTS_INTERFACE}:{board.board_code}",
                    is_fallback=True,
                    failure_reason=failure_reason,
                ),
            )
            for constituent in board.constituents
        ]

    def _concept_board_record(
        self,
        board: CachedConceptBoard,
        concept_name: str,
    ) -> ConceptBoardRecord:
        return ConceptBoardRecord(
            raw_name=concept_name,
            concept_name=concept_name,
            board_code=board.board_code,
            provider=self._metadata(
                board,
                provider_interface=f"{MARKET_METADATA_CACHE_INTERFACE}:concept_boards",
                is_fallback=False,
            ),
        )

    def _metadata(
        self,
        board: CachedConceptBoard,
        *,
        provider_interface: str,
        is_fallback: bool,
        failure_reason: str | None = None,
    ) -> ProviderMetadata:
        return ProviderMetadata(
            provider_name=board.provider_name,
            provider_interface=provider_interface,
            retrieved_at=board.retrieved_at,
            is_fallback=is_fallback,
            failure_reason=failure_reason,
        )


class MarketMetadataBackedProvider:
    """Provider wrapper that uses local market metadata before live AKShare discovery."""

    def __init__(
        self,
        primary: MarketDataProvider,
        metadata_store: MarketMetadataStore | None = None,
    ) -> None:
        self._primary = primary
        self._metadata_store = metadata_store or MarketMetadataStore.load()

    def list_stock_source_records(self) -> list[StockSourceRecord]:
        return self._primary.list_stock_source_records()

    def list_concept_boards(self) -> list[ConceptBoardRecord]:
        return self._metadata_store.list_concept_boards()

    def list_concept_constituents(
        self,
        concept_name: str,
    ) -> list[ConceptConstituentRecord]:
        board = self._metadata_store.find_concept_board(concept_name)
        if board is None:
            return self._primary.list_concept_constituents(concept_name)

        try:
            records = self._primary.list_concept_constituents(board.board_code)
            if records:
                return [
                    record.model_copy(
                        update={
                            "concept_name": board.canonical_name,
                        }
                    )
                    for record in records
                ]
            failure_reason = (
                f"live provider returned no concept constituents for {board.board_code}"
            )
        except Exception as exc:
            failure_reason = str(exc)

        cached_records = self._metadata_store.list_concept_constituents(
            board.canonical_name,
            failure_reason=failure_reason,
        )
        if cached_records:
            return cached_records
        raise ProviderUnavailableError(failure_reason)

    def get_business_profile(self, symbol: str) -> BusinessProfileRecord:
        return self._primary.get_business_profile(symbol)

    def get_financial_snapshot(self, symbol: str) -> FinancialSnapshotRecord:
        return self._primary.get_financial_snapshot(symbol)

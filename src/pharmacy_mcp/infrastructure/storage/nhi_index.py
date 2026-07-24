"""SQLite index for the official Taiwan NHI drug-item CSV."""

from __future__ import annotations

import asyncio
import csv
import os
import sqlite3
import tempfile
import threading
from collections.abc import Sequence
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

from pharmacy_mcp.config import settings

NHI_RESOURCE_ID = "A21030000I-E41001-001"
NHI_INDEX_SCHEMA_VERSION = "2"
NHI_DATASET_URL = (
    f"https://info.nhi.gov.tw/api/iode0000s01/Dataset?rId={NHI_RESOURCE_ID}"
)

_COLUMNS = (
    "mutation",
    "nhi_code",
    "english_name",
    "chinese_name",
    "ingredient",
    "strength",
    "strength_unit",
    "combination_type",
    "price",
    "effective_start",
    "effective_end",
    "vendor",
    "manufacturer",
    "dosage_form",
    "drug_category",
    "group_name",
    "atc_code",
    "coverage_rule_chapter",
    "license_url",
    "coverage_rule_url",
    "is_current",
)

_CSV_FIELDS = {
    "mutation": "異動",
    "nhi_code": "藥品代號",
    "english_name": "藥品英文名稱",
    "chinese_name": "藥品中文名稱",
    "ingredient": "成分",
    "strength": "規格量",
    "strength_unit": "規格單位",
    "combination_type": "單複方",
    "price": "支付價",
    "effective_start": "有效起日",
    "effective_end": "有效迄日",
    "vendor": "藥商",
    "manufacturer": "製造廠名稱",
    "dosage_form": "劑型",
    "drug_category": "藥品分類",
    "group_name": "分類分組名稱",
    "atc_code": "ATC代碼",
    "coverage_rule_chapter": "給付規定章節",
    "license_url": "藥品代碼超連結",
    "coverage_rule_url": "給付規定章節連結",
}


class NHIIndex:
    """Download, atomically index, and query the monthly NHI CSV dataset."""

    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        dataset_url: str = NHI_DATASET_URL,
        refresh_days: int | None = None,
        auto_download: bool | None = None,
    ) -> None:
        self.database_path = Path(database_path or settings.nhi_index_path)
        self.dataset_url = dataset_url
        self.refresh_days = refresh_days or settings.nhi_refresh_days
        self.auto_download = (
            settings.nhi_auto_download if auto_download is None else auto_download
        )
        self._build_lock = threading.Lock()

    async def ensure_ready(self) -> bool:
        """Ensure a fresh-enough index exists, downloading only when enabled."""

        return await asyncio.to_thread(self._ensure_ready_sync)

    async def search(
        self,
        query: str,
        *,
        limit: int = 20,
        current_only: bool = True,
    ) -> list[dict[str, Any]]:
        """Search code, names, ingredient, and ATC fields."""

        if not await self.ensure_ready():
            return []
        return await asyncio.to_thread(
            self._search_sync,
            query,
            limit,
            current_only,
        )

    async def get_by_code(self, nhi_code: str) -> dict[str, Any] | None:
        """Return the newest active record for an exact NHI code."""

        if not await self.ensure_ready():
            return None
        return await asyncio.to_thread(self._get_by_code_sync, nhi_code)

    def build_from_csv(self, csv_path: str | Path) -> int:
        """Build a new index atomically from an official-format CSV file."""

        source = Path(csv_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary_name = tempfile.mkstemp(
            prefix="nhi-index-",
            suffix=".sqlite3",
            dir=self.database_path.parent,
        )
        os.close(fd)
        temporary_path = Path(temporary_name)
        try:
            count = self._populate_database(temporary_path, source)
            os.replace(temporary_path, self.database_path)
            return count
        except Exception:
            temporary_path.unlink(missing_ok=True)
            raise

    def status(self) -> dict[str, Any]:
        """Return local index metadata without triggering a download."""

        if not self._is_valid_database():
            return {
                "ready": False,
                "database_path": str(self.database_path),
                "dataset_url": self.dataset_url,
                "auto_download": self.auto_download,
            }
        with closing(self._connect()) as connection:
            metadata = dict(connection.execute("SELECT key, value FROM metadata"))
        return {
            "ready": True,
            "database_path": str(self.database_path),
            "dataset_url": metadata.get("source_url", self.dataset_url),
            "indexed_at": metadata.get("indexed_at"),
            "row_count": int(metadata.get("row_count", "0")),
            "auto_download": self.auto_download,
        }

    def _ensure_ready_sync(self) -> bool:
        if self._is_fresh():
            return True
        if not self.auto_download:
            return self._is_valid_database()

        with self._build_lock:
            if self._is_fresh():
                return True
            csv_path = self._download_csv()
            try:
                self.build_from_csv(csv_path)
            finally:
                csv_path.unlink(missing_ok=True)
        return True

    def _download_csv(self) -> Path:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary_name = tempfile.mkstemp(
            prefix="nhi-dataset-",
            suffix=".csv",
            dir=self.database_path.parent,
        )
        os.close(fd)
        temporary_path = Path(temporary_name)
        try:
            timeout = httpx.Timeout(settings.nhi_download_timeout_seconds)
            with (
                httpx.Client(timeout=timeout, follow_redirects=True) as client,
                client.stream("GET", self.dataset_url) as response,
                temporary_path.open("wb") as output,
            ):
                response.raise_for_status()
                for chunk in response.iter_bytes():
                    output.write(chunk)
            return temporary_path
        except Exception:
            temporary_path.unlink(missing_ok=True)
            raise

    def _populate_database(self, database: Path, csv_path: Path) -> int:
        connection = sqlite3.connect(database)
        try:
            connection.executescript(
                """
                PRAGMA journal_mode = OFF;
                PRAGMA synchronous = OFF;
                CREATE TABLE nhi_drugs (
                    mutation TEXT NOT NULL,
                    nhi_code TEXT NOT NULL,
                    english_name TEXT NOT NULL,
                    chinese_name TEXT NOT NULL,
                    ingredient TEXT NOT NULL,
                    strength TEXT NOT NULL,
                    strength_unit TEXT NOT NULL,
                    combination_type TEXT NOT NULL,
                    price REAL,
                    effective_start TEXT NOT NULL,
                    effective_end TEXT NOT NULL,
                    vendor TEXT NOT NULL,
                    manufacturer TEXT NOT NULL,
                    dosage_form TEXT NOT NULL,
                    drug_category TEXT NOT NULL,
                    group_name TEXT NOT NULL,
                    atc_code TEXT NOT NULL,
                    coverage_rule_chapter TEXT NOT NULL,
                    license_url TEXT NOT NULL,
                    coverage_rule_url TEXT NOT NULL,
                    is_current INTEGER NOT NULL
                );
                CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                """
            )
            placeholders = ",".join("?" for _ in _COLUMNS)
            count = 0
            batch: list[tuple[Any, ...]] = []
            with csv_path.open("r", encoding="utf-8-sig", newline="") as source:
                reader = csv.DictReader(source)
                self._validate_headers(reader.fieldnames)
                for raw_row in reader:
                    batch.append(self._normalize_row(raw_row))
                    if len(batch) >= 2000:
                        connection.executemany(
                            f"INSERT INTO nhi_drugs VALUES ({placeholders})",  # nosec B608
                            batch,
                        )
                        count += len(batch)
                        batch.clear()
                if batch:
                    connection.executemany(
                        f"INSERT INTO nhi_drugs VALUES ({placeholders})",  # nosec B608
                        batch,
                    )
                    count += len(batch)
            connection.executescript(
                """
                CREATE INDEX idx_nhi_code ON nhi_drugs(nhi_code);
                CREATE INDEX idx_nhi_english ON nhi_drugs(english_name);
                CREATE INDEX idx_nhi_ingredient ON nhi_drugs(ingredient);
                CREATE INDEX idx_nhi_atc ON nhi_drugs(atc_code);
                CREATE INDEX idx_nhi_current ON nhi_drugs(is_current);
                """
            )
            connection.executemany(
                "INSERT INTO metadata(key, value) VALUES (?, ?)",
                (
                    ("source_url", self.dataset_url),
                    ("resource_id", NHI_RESOURCE_ID),
                    ("schema_version", NHI_INDEX_SCHEMA_VERSION),
                    ("indexed_at", datetime.now(UTC).isoformat()),
                    ("row_count", str(count)),
                ),
            )
            connection.commit()
            return count
        finally:
            connection.close()

    def _search_sync(
        self,
        query: str,
        limit: int,
        current_only: bool,
    ) -> list[dict[str, Any]]:
        term = f"%{query.casefold()}%"
        current_clause = "AND is_current = 1" if current_only else ""
        # Column names and the optional clause are internal constants; search
        # text and limit remain bound parameters.
        statement = f"""
            SELECT {",".join(_COLUMNS)} FROM nhi_drugs
            WHERE (
                lower(nhi_code) LIKE ? OR lower(english_name) LIKE ? OR
                lower(chinese_name) LIKE ? OR lower(ingredient) LIKE ? OR
                lower(atc_code) LIKE ?
            ) {current_clause}
            ORDER BY is_current DESC, effective_start DESC, nhi_code
            LIMIT ?
        """  # nosec B608
        with closing(self._connect()) as connection:
            rows = connection.execute(statement, (*([term] * 5), limit)).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def _get_by_code_sync(self, nhi_code: str) -> dict[str, Any] | None:
        # Column names are internal constants; the NHI code remains bound.
        statement = f"""
            SELECT {",".join(_COLUMNS)} FROM nhi_drugs
            WHERE upper(nhi_code) = upper(?)
            ORDER BY is_current DESC, effective_start DESC
            LIMIT 1
        """  # nosec B608
        with closing(self._connect()) as connection:
            row = connection.execute(statement, (nhi_code,)).fetchone()
        return self._row_to_dict(row) if row else None

    def _row_to_dict(self, row: tuple[Any, ...]) -> dict[str, Any]:
        result = dict(zip(_COLUMNS, row, strict=True))
        result["is_current"] = bool(result["is_current"])
        result["source"] = "Taiwan NHI Open Data"
        result["dataset_resource_id"] = NHI_RESOURCE_ID
        return result

    def _normalize_row(self, row: dict[str, str]) -> tuple[Any, ...]:
        normalized: dict[str, Any] = {
            key: (row.get(csv_name) or "").strip()
            for key, csv_name in _CSV_FIELDS.items()
        }
        try:
            normalized["price"] = float(normalized["price"])
        except ValueError:
            normalized["price"] = None
        normalized["is_current"] = int(_is_current_date(normalized["effective_end"]))
        return tuple(normalized[column] for column in _COLUMNS)

    def _validate_headers(self, fieldnames: Sequence[str] | None) -> None:
        available = set(fieldnames or [])
        missing = set(_CSV_FIELDS.values()) - available
        if missing:
            raise ValueError(
                f"NHI CSV is missing columns: {', '.join(sorted(missing))}"
            )

    def _is_valid_database(self) -> bool:
        if not self.database_path.is_file():
            return False
        try:
            with closing(self._connect()) as connection:
                metadata = dict(connection.execute("SELECT key, value FROM metadata"))
                return (
                    metadata.get("indexed_at") is not None
                    and metadata.get("schema_version") == NHI_INDEX_SCHEMA_VERSION
                )
        except sqlite3.DatabaseError:
            return False

    def _is_fresh(self) -> bool:
        if not self._is_valid_database():
            return False
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT value FROM metadata WHERE key = 'indexed_at'"
            ).fetchone()
        if row is None:
            return False
        indexed_at = datetime.fromisoformat(row[0])
        return datetime.now(UTC) - indexed_at < timedelta(days=self.refresh_days)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.database_path)


def _is_current_date(effective_end: str) -> bool:
    if not effective_end or effective_end == "9991231":
        return True
    try:
        return int(effective_end) >= int(_roc_today())
    except ValueError:
        return False


def _roc_today() -> str:
    today = datetime.now(UTC).date()
    return f"{today.year - 1911:03d}{today.month:02d}{today.day:02d}"

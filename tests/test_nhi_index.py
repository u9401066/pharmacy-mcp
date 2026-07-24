"""Tests for the official Taiwan NHI CSV-to-SQLite index."""

from pathlib import Path

import pytest

from pharmacy_mcp.infrastructure.api.nhi import NHIClient
from pharmacy_mcp.infrastructure.storage.nhi_index import NHIIndex

CSV_HEADER = (
    "異動,藥品代號,藥品英文名稱,藥品中文名稱,成分,規格量,規格單位,"
    "單複方,支付價,有效起日,有效迄日,藥商,製造廠名稱,劑型,藥品分類,"
    "分類分組名稱,ATC代碼,給付規定章節,藥品代碼超連結,給付規定章節連結\n"
)

CSV_ROWS = (
    ",A000000001,Warfarin tablets,華法林錠,WARFARIN SODIUM,5,MG,單方,"
    "4.50,990101,990731,Vendor,Factory,錠劑,一般藥品,Warfarin,B01AA03,"
    "2.1,https://example.test/license,https://example.test/rule\n"
    ",A000000001,Warfarin tablets,華法林錠,WARFARIN SODIUM,5,MG,單方,"
    "4.20,1150101,9991231,Vendor,Factory,錠劑,一般藥品,Warfarin,B01AA03,"
    "2.1,https://example.test/license,https://example.test/rule\n"
    ",A000000002,Aspirin tablets,阿斯匹靈錠,ASPIRIN,100,MG,單方,1.50,"
    "1150101,9991231,Vendor,Factory,錠劑,一般藥品,Aspirin,B01AC06,,"
    "https://example.test/license,\n"
)


@pytest.fixture
def index(tmp_path: Path) -> NHIIndex:
    source = tmp_path / "nhi.csv"
    source.write_text(CSV_HEADER + CSV_ROWS, encoding="utf-8-sig")
    result = NHIIndex(
        tmp_path / "nhi.sqlite3",
        dataset_url="https://example.test/nhi.csv",
        auto_download=False,
    )
    assert result.build_from_csv(source) == 3
    return result


def test_index_status_contains_provenance(index: NHIIndex) -> None:
    status = index.status()

    assert status["ready"] is True
    assert status["row_count"] == 3
    assert status["dataset_url"] == "https://example.test/nhi.csv"


@pytest.mark.asyncio
async def test_search_returns_only_current_records_by_default(index: NHIIndex) -> None:
    results = await index.search("warfarin")

    assert len(results) == 1
    assert results[0]["nhi_code"] == "A000000001"
    assert results[0]["price"] == 4.2
    assert results[0]["is_current"] is True
    assert results[0]["dataset_resource_id"] == "A21030000I-E41001-001"


@pytest.mark.asyncio
async def test_six_digit_roc_end_date_is_historical(index: NHIIndex) -> None:
    results = await index.search("warfarin", current_only=False)

    assert len(results) == 2
    historical = next(item for item in results if item["effective_end"] == "990731")
    assert historical["is_current"] is False


@pytest.mark.asyncio
async def test_exact_code_returns_newest_current_record(index: NHIIndex) -> None:
    result = await index.get_by_code("a000000001")

    assert result is not None
    assert result["effective_start"] == "1150101"


@pytest.mark.asyncio
async def test_nhi_client_queries_official_index_adapter(index: NHIIndex) -> None:
    client = NHIClient(index=index, auto_download=False)

    results = await client.search_by_drug_name("阿斯匹靈")

    assert len(results) == 1
    assert results[0]["ingredient"] == "ASPIRIN"

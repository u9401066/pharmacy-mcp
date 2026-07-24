"""Probe shipped public pharmaceutical sources without downloading datasets."""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Awaitable
from datetime import UTC, datetime
from typing import Any

import httpx

from pharmacy_mcp.infrastructure.api.chembl import ChEMBLClient
from pharmacy_mcp.infrastructure.api.clinical_trials import ClinicalTrialsClient
from pharmacy_mcp.infrastructure.api.dailymed import DailyMedClient
from pharmacy_mcp.infrastructure.api.fda import FDAClient
from pharmacy_mcp.infrastructure.api.medlineplus import MedlinePlusClient
from pharmacy_mcp.infrastructure.api.open_targets import OpenTargetsClient
from pharmacy_mcp.infrastructure.api.pubchem import PubChemClient
from pharmacy_mcp.infrastructure.api.pubmed import PubMedClient
from pharmacy_mcp.infrastructure.api.rxnorm import RxNormClient
from pharmacy_mcp.infrastructure.api.tfda import TFDAClient
from pharmacy_mcp.infrastructure.storage.nhi_index import NHI_DATASET_URL

PROBE_TIMEOUT_SECONDS = 45.0


async def _probe(name: str, operation: Awaitable[object]) -> dict[str, object]:
    started = time.monotonic()
    try:
        await asyncio.wait_for(operation, timeout=PROBE_TIMEOUT_SECONDS)
    except Exception as exc:
        return {
            "source": name,
            "status": "error",
            "duration_ms": round((time.monotonic() - started) * 1_000),
            "error_type": type(exc).__name__,
            "message": str(exc)[:500],
        }
    return {
        "source": name,
        "status": "ok",
        "duration_ms": round((time.monotonic() - started) * 1_000),
    }


async def _stream_status(url: str) -> None:
    """Validate status and headers without consuming a potentially large dataset."""

    async with (
        httpx.AsyncClient(timeout=PROBE_TIMEOUT_SECONDS) as client,
        client.stream("GET", url) as response,
    ):
        response.raise_for_status()


async def check_sources() -> dict[str, Any]:
    """Run bounded public-source probes concurrently and return one JSON report."""

    fda = FDAClient()
    rxnorm = RxNormClient()
    operations: tuple[tuple[str, Awaitable[object]], ...] = (
        ("rxnorm", rxnorm.search_by_name("warfarin", 1)),
        ("rxclass", rxnorm.get_drug_class_memberships("11289")),
        ("openfda-label", fda.search_drug_labels("warfarin", 1)),
        ("openfda-event", fda.get_adverse_events("warfarin", 1)),
        ("openfda-ndc", fda.search_ndc("warfarin", 1)),
        ("openfda-enforcement", fda.search_recalls("warfarin", 1)),
        ("openfda-drugsfda", fda.search_approvals("warfarin", 1)),
        ("openfda-orangebook", fda.search_orange_book("warfarin", 1)),
        ("openfda-shortages", fda.search_shortages("amoxicillin", 1)),
        ("dailymed", DailyMedClient().search_spls("warfarin", 1)),
        ("pubchem", PubChemClient().get_compound_by_name("warfarin")),
        ("pubmed", PubMedClient().search_articles("warfarin", 1)),
        (
            "clinical-trials-gov",
            ClinicalTrialsClient().search_studies("warfarin", 1),
        ),
        ("chembl", ChEMBLClient().search_molecules("warfarin", 1)),
        ("open-targets", OpenTargetsClient().search_drugs("warfarin", 1)),
        (
            "medlineplus-connect",
            MedlinePlusClient().search_medication(drug_name="warfarin"),
        ),
        ("tw-tfda", _stream_status(TFDAClient.ACTIVE_PERMITS_JSON_URL)),
        ("tw-nhi", _stream_status(NHI_DATASET_URL)),
    )
    checks = await asyncio.gather(*(_probe(name, call) for name, call in operations))
    failed = sum(check["status"] == "error" for check in checks)
    return {
        "checked_at": datetime.now(UTC).isoformat(),
        "status": "error" if failed else "ok",
        "check_count": len(checks),
        "failed_count": failed,
        "checks": checks,
    }


def main() -> None:
    """Print the report and fail the process if any public source probe failed."""

    report = asyncio.run(check_sources())
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    if report["status"] != "ok":
        raise SystemExit(1)


if __name__ == "__main__":
    main()

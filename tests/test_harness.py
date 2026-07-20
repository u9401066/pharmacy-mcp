"""Tests for the programmatic/CLI harness and MCP agent prompt."""

import json

import pytest
from mcp import types

from pharmacy_mcp.application.harness import PharmacyHarness, build_agent_contract
from pharmacy_mcp.domain.models.response import (
    OutputFormat,
    QueryResponse,
    ResponseStatus,
)
from pharmacy_mcp.infrastructure.providers.builtin import FormularyKnowledgeProvider
from pharmacy_mcp.infrastructure.providers.registry import ProviderRegistry
from pharmacy_mcp.presentation.cli import run_cli
from pharmacy_mcp.presentation.server import create_server


def _local_harness() -> PharmacyHarness:
    registry = ProviderRegistry()
    registry.register(FormularyKnowledgeProvider())
    return PharmacyHarness(registry, provider_timeout=0.1)


@pytest.mark.asyncio
async def test_harness_returns_validated_single_entry_response() -> None:
    response = await _local_harness().query(
        "warfarin",
        sources=["local-formulary"],
        capabilities=["formulary"],
        output_format="json_compact",
        locale="zh-TW",
    )

    assert response.status is ResponseStatus.OK
    assert response.meta.output_format is OutputFormat.JSON_COMPACT
    assert (
        response.data["provider_results"]["local-formulary"][0]["generic_name"]
        == "Warfarin"
    )
    assert QueryResponse.model_validate(response.model_dump()) == response


def test_agent_contract_constrains_forwarded_output() -> None:
    contract = build_agent_contract(OutputFormat.JSON_COMPACT, "zh-TW")

    assert "structuredContent" in contract
    assert "output_format=json_compact" in contract
    assert "no prose or code fence" in contract
    assert "Do not invent" in contract


@pytest.mark.asyncio
async def test_mcp_exposes_parameterized_agent_contract_prompt() -> None:
    server = create_server()
    request = types.GetPromptRequest(
        params=types.GetPromptRequestParams(
            name="pharmacy-query-contract",
            arguments={"output_format": "json_compact", "locale": "zh-TW"},
        )
    )

    result = await server.request_handlers[types.GetPromptRequest](request)
    prompt = result.root
    assert isinstance(prompt, types.GetPromptResult)
    assert isinstance(prompt.messages[0].content, types.TextContent)
    assert "output_format=json_compact" in prompt.messages[0].content.text


def test_cli_emits_only_query_response(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        "pharmacy_mcp.presentation.cli.PharmacyHarness",
        _local_harness,
    )

    exit_code = run_cli(
        [
            "warfarin",
            "--source",
            "local-formulary",
            "--capability",
            "formulary",
            "--format",
            "json_compact",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert set(payload) == {
        "schema_version",
        "status",
        "data",
        "sources",
        "warnings",
        "errors",
        "meta",
    }


def test_cli_returns_error_status_for_unavailable_provider(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "pharmacy_mcp.presentation.cli.PharmacyHarness",
        _local_harness,
    )

    exit_code = run_cli(["warfarin", "--source", "drugbank"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert payload["status"] == "error"
    assert payload["errors"][0]["code"] == "provider_unavailable"

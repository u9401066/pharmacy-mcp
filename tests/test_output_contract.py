"""Tests for the versioned, agent-facing MCP output contract."""

import json

from mcp.types import Tool

from pharmacy_mcp.config import settings
from pharmacy_mcp.domain.models.response import OutputFormat, QueryResponse
from pharmacy_mcp.presentation.formatting import ResponseFormatter
from pharmacy_mcp.presentation.server import OUTPUT_SCHEMA, _decorate_tools


def _response(output_format: OutputFormat = OutputFormat.JSON) -> QueryResponse:
    return QueryResponse.success(
        tool="search_drug",
        data={"results": [{"name": "warfarin"}]},
        output_format=output_format,
        locale="zh-TW",
        disclaimer=settings.disclaimer,
    )


def test_response_contract_forbids_unknown_top_level_fields() -> None:
    schema = QueryResponse.model_json_schema()

    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {
        "schema_version",
        "status",
        "data",
        "sources",
        "warnings",
        "errors",
        "meta",
    }


def test_response_count_is_inferred_from_results() -> None:
    response = _response()

    assert response.schema_version == "1.0"
    assert response.meta.result_count == 1
    assert response.status == "ok"


def test_json_compact_renderer_is_deterministic() -> None:
    rendered = ResponseFormatter.render(
        _response(OutputFormat.JSON_COMPACT),
        OutputFormat.JSON_COMPACT,
    )

    assert "\n" not in rendered
    assert json.loads(rendered)["data"]["results"][0]["name"] == "warfarin"


def test_markdown_renderer_keeps_envelope_metadata() -> None:
    rendered = ResponseFormatter.render(
        _response(OutputFormat.MARKDOWN),
        OutputFormat.MARKDOWN,
    )

    assert "Schema: `1.0`" in rendered
    assert "Status: `ok`" in rendered
    assert '"name": "warfarin"' in rendered


def test_all_tools_receive_common_input_and_output_schema() -> None:
    tool = Tool(
        name="example",
        description="Example.",
        inputSchema={"type": "object", "properties": {}},
    )

    decorated = _decorate_tools([tool])[0]

    assert decorated.inputSchema["properties"]["output_format"]["enum"] == [
        "json",
        "json_compact",
        "markdown",
    ]
    assert decorated.inputSchema["properties"]["locale"]["default"] == "zh-TW"
    assert decorated.outputSchema == OUTPUT_SCHEMA
    assert "structuredContent as the source of truth" in decorated.description

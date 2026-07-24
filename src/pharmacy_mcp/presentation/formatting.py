"""Deterministic renderers for the canonical Pharmacy MCP response."""

from __future__ import annotations

import json
from typing import Any

from pharmacy_mcp.domain.models.response import OutputFormat, QueryResponse


class ResponseFormatter:
    """Render a validated envelope while preserving structured content."""

    @staticmethod
    def render(response: QueryResponse, output_format: OutputFormat) -> str:
        """Render ``response`` in the requested transport text format."""

        payload = response.model_dump(mode="json")
        if output_format is OutputFormat.JSON_COMPACT:
            return json.dumps(
                payload,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            )
        if output_format is OutputFormat.MARKDOWN:
            return _render_markdown(payload)
        return json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )


def _render_markdown(payload: dict[str, Any]) -> str:
    """Render a predictable Markdown view without losing nested payload data."""

    status = payload["status"]
    meta = payload["meta"]
    data_json = json.dumps(
        payload.get("data"),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
    lines = [
        f"# Pharmacy query: `{meta['tool']}`",
        "",
        f"- Schema: `{payload['schema_version']}`",
        f"- Status: `{status}`",
        f"- Locale: `{meta['locale']}`",
        "",
        "## Data",
        "",
        "```json",
        data_json,
        "```",
    ]
    if payload["warnings"]:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in payload["warnings"])
    if payload["errors"]:
        lines.extend(["", "## Errors", ""])
        lines.extend(
            f"- `{error['code']}`: {error['message']}" for error in payload["errors"]
        )
    lines.extend(["", "> " + meta["disclaimer"]])
    return "\n".join(lines)

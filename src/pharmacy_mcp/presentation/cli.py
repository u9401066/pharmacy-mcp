"""Command-line interface for the Pharmacy MCP agent harness."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections.abc import Sequence

from pharmacy_mcp.application.harness import PharmacyHarness
from pharmacy_mcp.config import settings
from pharmacy_mcp.domain.models.provider import QueryCapability
from pharmacy_mcp.domain.models.response import OutputFormat, ResponseStatus


def build_parser() -> argparse.ArgumentParser:
    """Build the deterministic command-line contract."""

    parser = argparse.ArgumentParser(
        prog="pharmacy-query",
        description="Query pharmaceutical sources through the unified agent harness.",
    )
    parser.add_argument("query", help="Drug, identifier, indication, or question")
    parser.add_argument(
        "--capability",
        action="append",
        choices=[item.value for item in QueryCapability],
        dest="capabilities",
        help="Required capability; repeat for multiple capabilities",
    )
    parser.add_argument(
        "--source",
        action="append",
        dest="sources",
        help="Explicit provider ID; repeat for multiple sources",
    )
    parser.add_argument("--limit", type=int, default=10, choices=range(1, 101))
    parser.add_argument(
        "--format",
        choices=[item.value for item in OutputFormat],
        default=settings.default_output_format,
        dest="output_format",
    )
    parser.add_argument("--locale", default=settings.default_locale)
    parser.add_argument(
        "--context-json",
        default="{}",
        help="Authorized provider context as a JSON object; never put secrets here",
    )
    return parser


def run_cli(argv: Sequence[str] | None = None) -> int:
    """Execute one query and return a process status code."""

    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        context = json.loads(args.context_json)
    except json.JSONDecodeError as exc:
        parser.error(f"--context-json is not valid JSON: {exc.msg}")
    if not isinstance(context, dict):
        parser.error("--context-json must decode to a JSON object")

    harness = PharmacyHarness()
    response = asyncio.run(
        harness.query(
            args.query,
            capabilities=args.capabilities,
            sources=args.sources,
            limit=args.limit,
            context=context,
            output_format=args.output_format,
            locale=args.locale,
        )
    )
    sys.stdout.write(harness.render(response) + "\n")
    return 2 if response.status is ResponseStatus.ERROR else 0


def main() -> None:
    """Console-script entry point."""

    raise SystemExit(run_cli())


if __name__ == "__main__":
    main()

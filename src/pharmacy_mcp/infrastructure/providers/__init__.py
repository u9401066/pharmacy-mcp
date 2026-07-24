"""Knowledge provider registry and built-in adapters."""

from pharmacy_mcp.infrastructure.providers.registry import (
    ProviderRegistry,
    build_default_registry,
)

__all__ = ["ProviderRegistry", "build_default_registry"]

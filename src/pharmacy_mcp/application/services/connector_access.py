"""Explicit retrieval and inspection services for configured connectors."""

from __future__ import annotations

from dataclasses import asdict

from pharmacy_mcp.domain.models.response import (
    ErrorDetail,
    ResponseStatus,
    ServiceResult,
    SourceReference,
)
from pharmacy_mcp.infrastructure.providers.builtin import FHIRKnowledgeProvider
from pharmacy_mcp.infrastructure.providers.file import FileKnowledgeProvider
from pharmacy_mcp.infrastructure.providers.registry import ProviderRegistry


class ConnectorAccessService:
    """Expose safe connector-specific operations through application contracts."""

    def __init__(self, registry: ProviderRegistry) -> None:
        self.registry = registry

    async def read_document(
        self,
        document_id: str,
        *,
        offset: int = 0,
        max_chars: int = 10_000,
    ) -> ServiceResult:
        """Read a bounded document span using only a prior opaque result ID."""

        provider = self.registry.get("file")
        if not isinstance(provider, FileKnowledgeProvider):
            return ServiceResult(
                status=ResponseStatus.ERROR,
                data={"configured": False, "document_id": document_id},
                errors=[
                    ErrorDetail(
                        code="file_provider_unavailable",
                        message="The configured file knowledge provider is unavailable.",
                        provider="file",
                    )
                ],
            )
        try:
            document = await provider.read_document(
                document_id,
                offset=offset,
                max_chars=max_chars,
            )
        except ValueError as exc:
            return ServiceResult(
                status=ResponseStatus.ERROR,
                data={"configured": True, "document_id": document_id},
                errors=[
                    ErrorDetail(
                        code="document_not_found",
                        message=str(exc),
                        provider="file",
                    )
                ],
            )

        data = asdict(document)
        data["configured"] = True
        return ServiceResult(
            status=ResponseStatus.OK,
            data=data,
            sources=[
                SourceReference(
                    provider="file",
                    title=document.title,
                    uri=(
                        f"pharmacy-document://{document.document_id}"
                        f"#char={document.char_start}-{document.char_end}"
                    ),
                    version=document.text_sha256,
                )
            ],
        )

    async def inspect_fhir_server(self) -> ServiceResult:
        """Inspect configured FHIR capabilities using a bounded safe projection."""

        provider = self.registry.get("fhir")
        if not isinstance(provider, FHIRKnowledgeProvider):
            return ServiceResult(
                status=ResponseStatus.ERROR,
                data={"configured": False},
                errors=[
                    ErrorDetail(
                        code="fhir_provider_unavailable",
                        message=(
                            "FHIR is not configured. Set "
                            "PHARMACY_MCP_FHIR_BASE_URL to enable it."
                        ),
                        provider="fhir",
                    )
                ],
            )
        try:
            capabilities = await provider.inspect_capabilities()
        except Exception as exc:
            return ServiceResult(
                status=ResponseStatus.ERROR,
                data={"configured": True},
                errors=[
                    ErrorDetail(
                        code="fhir_capability_error",
                        message=str(exc),
                        provider="fhir",
                        retryable=True,
                    )
                ],
            )

        unsupported = capabilities.get("unsupported_configured_resources", [])
        warnings = []
        if unsupported:
            warnings.append(
                "Configured FHIR resource types not advertised by this server: "
                + ", ".join(str(item) for item in unsupported)
            )
        return ServiceResult(
            status=ResponseStatus.PARTIAL if warnings else ResponseStatus.OK,
            data={"configured": True, **capabilities},
            sources=[
                SourceReference(
                    provider="fhir",
                    title="Configured hospital FHIR CapabilityStatement",
                    uri=str(capabilities["server"]) + "metadata",
                    version=str(capabilities.get("reported_fhir_version") or ""),
                )
            ],
            warnings=warnings,
        )

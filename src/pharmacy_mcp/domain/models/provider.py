"""Knowledge-provider capabilities and execution contracts."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field

from pharmacy_mcp.domain.models.response import (
    ErrorDetail,
    ResponseStatus,
    SourceReference,
)


class QueryCapability(StrEnum):
    """Normalized capabilities understood by the unified query harness."""

    SEARCH = "search"
    IDENTITY = "identity"
    LABEL = "label"
    DOSING = "dosing"
    SAFETY = "safety"
    INTERACTION = "interaction"
    ADVERSE_EVENT = "adverse_event"
    DRUG_CLASS = "drug_class"
    NDC = "ndc"
    APPROVAL = "approval"
    REIMBURSEMENT = "reimbursement"
    FORMULARY = "formulary"
    INVENTORY = "inventory"
    DOCUMENT = "document"
    CHEMISTRY = "chemistry"
    LITERATURE = "literature"
    RECALL = "recall"
    SHORTAGE = "shortage"


class ProviderState(StrEnum):
    """Honest implementation/readiness state shown to agents and operators."""

    READY = "ready"
    CONFIGURABLE = "configurable"
    LICENSE_REQUIRED = "license_required"
    DEPRECATED = "deprecated"


class ProviderKind(StrEnum):
    """Origin category used for policy and routing decisions."""

    PUBLIC_API = "public_api"
    TAIWAN_OPEN_DATA = "taiwan_open_data"
    HEALTHCARE = "healthcare"
    LOCAL = "local"
    LICENSED_API = "licensed_api"
    WEB = "web"


class ProviderDescriptor(BaseModel):
    """Discoverable metadata for an executable or cataloged source."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    title: str
    kind: ProviderKind
    state: ProviderState
    capabilities: tuple[QueryCapability, ...]
    documentation_url: str | None = None
    enabled_by_default: bool = False
    requires_credentials: bool = False
    notes: str | None = None


class ProviderQuery(BaseModel):
    """Normalized query passed to every provider adapter."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    text: str = Field(min_length=1, max_length=500)
    capabilities: tuple[QueryCapability, ...] = (QueryCapability.SEARCH,)
    limit: int = Field(default=10, ge=1, le=100)
    context: dict[str, Any] = Field(default_factory=dict)


class ProviderResult(BaseModel):
    """One provider's isolated result, including provenance and failures."""

    model_config = ConfigDict(extra="forbid")

    provider_id: str
    status: ResponseStatus = ResponseStatus.OK
    data: Any
    sources: list[SourceReference] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[ErrorDetail] = Field(default_factory=list)


class KnowledgeProvider(Protocol):
    """Port implemented by APIs, FHIR, DBs, documents, and web adapters."""

    descriptor: ProviderDescriptor

    async def query(self, request: ProviderQuery) -> ProviderResult:
        """Execute a normalized knowledge query."""

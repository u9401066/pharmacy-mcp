"""Curated catalog of pharmaceutical data-source integration points."""

from pharmacy_mcp.domain.models.provider import (
    ProviderDescriptor,
    ProviderKind,
    ProviderState,
    QueryCapability,
)

C = QueryCapability

PROVIDER_CATALOG: tuple[ProviderDescriptor, ...] = (
    ProviderDescriptor(
        id="rxnorm",
        title="NLM RxNorm / RxNav",
        kind=ProviderKind.PUBLIC_API,
        state=ProviderState.READY,
        capabilities=(C.SEARCH, C.IDENTITY, C.DRUG_CLASS),
        documentation_url="https://lhncbc.nlm.nih.gov/RxNav/APIs/RxNormAPIs.html",
        enabled_by_default=True,
    ),
    ProviderDescriptor(
        id="rxclass",
        title="NLM RxClass",
        kind=ProviderKind.PUBLIC_API,
        state=ProviderState.READY,
        capabilities=(C.DRUG_CLASS, C.IDENTITY),
        documentation_url="https://lhncbc.nlm.nih.gov/RxNav/APIs/RxClassAPIs.html",
        enabled_by_default=True,
        notes="Resolves RxCUIs through RxNorm, then executes RxClass membership lookup.",
    ),
    ProviderDescriptor(
        id="openfda",
        title="FDA openFDA Drug APIs",
        kind=ProviderKind.PUBLIC_API,
        state=ProviderState.READY,
        capabilities=(
            C.SEARCH,
            C.LABEL,
            C.DOSING,
            C.SAFETY,
            C.INTERACTION,
            C.ADVERSE_EVENT,
            C.NDC,
            C.APPROVAL,
            C.THERAPEUTIC_EQUIVALENCE,
            C.RECALL,
            C.SHORTAGE,
        ),
        documentation_url="https://open.fda.gov/apis/drug/",
        enabled_by_default=True,
        notes="Public data is not validated for direct clinical decision-making.",
    ),
    ProviderDescriptor(
        id="dailymed",
        title="NLM DailyMed SPL v2",
        kind=ProviderKind.PUBLIC_API,
        state=ProviderState.READY,
        capabilities=(C.SEARCH, C.LABEL, C.DOSING, C.SAFETY),
        documentation_url="https://dailymed.nlm.nih.gov/dailymed/app-support-web-services.cfm",
        enabled_by_default=True,
    ),
    ProviderDescriptor(
        id="pubchem",
        title="NIH PubChem PUG REST",
        kind=ProviderKind.PUBLIC_API,
        state=ProviderState.READY,
        capabilities=(C.IDENTITY, C.CHEMISTRY),
        documentation_url="https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest",
    ),
    ProviderDescriptor(
        id="medlineplus-connect",
        title="NLM MedlinePlus Connect",
        kind=ProviderKind.PUBLIC_API,
        state=ProviderState.READY,
        capabilities=(C.DOCUMENT, C.LITERATURE),
        documentation_url="https://medlineplus.gov/medlineplus-connect/web-service/",
    ),
    ProviderDescriptor(
        id="drugbank",
        title="DrugBank API",
        kind=ProviderKind.LICENSED_API,
        state=ProviderState.LICENSE_REQUIRED,
        capabilities=(C.IDENTITY, C.INTERACTION, C.DOSING, C.SAFETY),
        documentation_url="https://dev.drugbank.com/",
        requires_credentials=True,
    ),
    ProviderDescriptor(
        id="first-databank",
        title="First Databank",
        kind=ProviderKind.LICENSED_API,
        state=ProviderState.LICENSE_REQUIRED,
        capabilities=(C.INTERACTION, C.DOSING, C.SAFETY),
        requires_credentials=True,
    ),
    ProviderDescriptor(
        id="micromedex",
        title="Merative Micromedex",
        kind=ProviderKind.LICENSED_API,
        state=ProviderState.LICENSE_REQUIRED,
        capabilities=(C.INTERACTION, C.DOSING, C.SAFETY),
        requires_credentials=True,
    ),
    ProviderDescriptor(
        id="tw-tfda",
        title="Taiwan FDA Drug Permit Open Data",
        kind=ProviderKind.TAIWAN_OPEN_DATA,
        state=ProviderState.READY,
        capabilities=(C.SEARCH, C.IDENTITY, C.LABEL),
        documentation_url="https://data.gov.tw/dataset/9122",
        enabled_by_default=True,
    ),
    ProviderDescriptor(
        id="tw-nhi",
        title="Taiwan NHI Drug Items and Coverage",
        kind=ProviderKind.TAIWAN_OPEN_DATA,
        state=ProviderState.READY,
        capabilities=(C.SEARCH, C.REIMBURSEMENT),
        documentation_url="https://info.nhi.gov.tw/IODE0000/IODE0000S09?id=111",
        enabled_by_default=True,
    ),
    ProviderDescriptor(
        id="fhir",
        title="Hospital FHIR R4/R5",
        kind=ProviderKind.HEALTHCARE,
        state=ProviderState.READY,
        capabilities=(C.IDENTITY, C.FORMULARY, C.INVENTORY),
        documentation_url="https://hl7.org/fhir/",
        enabled_by_default=True,
        requires_credentials=True,
        notes="Base URL and SMART/Bearer authentication are supplied by the hospital.",
    ),
    ProviderDescriptor(
        id="local-formulary",
        title="Local Hospital Formulary",
        kind=ProviderKind.LOCAL,
        state=ProviderState.READY,
        capabilities=(C.SEARCH, C.FORMULARY),
        enabled_by_default=True,
    ),
    ProviderDescriptor(
        id="sql",
        title="SQL Knowledge Source",
        kind=ProviderKind.LOCAL,
        state=ProviderState.READY,
        capabilities=(C.SEARCH, C.FORMULARY, C.INVENTORY),
        enabled_by_default=True,
    ),
    ProviderDescriptor(
        id="vector",
        title="Vector Knowledge Source",
        kind=ProviderKind.LOCAL,
        state=ProviderState.READY,
        capabilities=(C.SEARCH, C.DOCUMENT, C.LITERATURE),
        enabled_by_default=True,
    ),
    ProviderDescriptor(
        id="file",
        title="PDF/DOCX/CSV/XLSX/Markdown Files",
        kind=ProviderKind.LOCAL,
        state=ProviderState.READY,
        capabilities=(C.SEARCH, C.DOCUMENT),
        enabled_by_default=True,
    ),
    ProviderDescriptor(
        id="web",
        title="Allowlisted Web Knowledge",
        kind=ProviderKind.WEB,
        state=ProviderState.READY,
        capabilities=(C.SEARCH, C.DOCUMENT, C.LITERATURE),
        enabled_by_default=True,
    ),
)

PROVIDER_BY_ID = {provider.id: provider for provider in PROVIDER_CATALOG}


def get_provider_descriptor(provider_id: str) -> ProviderDescriptor:
    """Return catalog metadata for a provider adapter."""

    try:
        return PROVIDER_BY_ID[provider_id]
    except KeyError as exc:
        raise KeyError(f"Unknown provider: {provider_id}") from exc

"""MCP Server configuration."""

from typing import Any, Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_prefix="PHARMACY_MCP_",
        env_file=".env",
    )

    # API URLs
    rxnorm_base_url: str = "https://rxnav.nlm.nih.gov/REST"
    fda_base_url: str = "https://api.fda.gov"
    dailymed_base_url: str = "https://dailymed.nlm.nih.gov/dailymed/services"
    pubchem_base_url: str = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
    medlineplus_service_url: str = "https://connect.medlineplus.gov/service"

    # Hospital FHIR. Adapter registers only when base URL is configured.
    fhir_base_url: str | None = None
    fhir_bearer_token: SecretStr | None = None
    fhir_version: Literal["R4", "R5"] = "R4"
    fhir_verify_tls: bool = True
    fhir_timeout_seconds: float = 20.0
    fhir_medication_resources: str = "MedicationKnowledge,Medication"
    fhir_inventory_resources: str = "InventoryItem,InventoryReport,SupplyDelivery"

    # Local/organization knowledge connectors
    file_roots: str = "knowledge"
    file_max_bytes: int = 20 * 1024 * 1024
    file_max_files: int = 500
    sql_database_path: str | None = None
    sql_tables: list[dict[str, Any]] = Field(default_factory=list)
    vector_search_url: str | None = None
    vector_api_key: SecretStr | None = None
    vector_verify_tls: bool = True
    web_urls: list[str] = Field(default_factory=list)
    web_max_bytes: int = 2 * 1024 * 1024

    # Cache settings
    cache_dir: str = ".cache"
    cache_ttl_seconds: int = 86400  # 24 hours

    # API settings
    request_timeout: int = 30
    max_retries: int = 3
    provider_timeout_seconds: float = 20.0

    # Taiwan NHI official monthly CSV index (~100 MB source download)
    nhi_index_path: str = ".cache/nhi/drug-items.sqlite3"
    nhi_auto_download: bool = True
    nhi_refresh_days: int = 7
    nhi_download_timeout_seconds: float = 300.0

    # Stable agent-facing response contract
    default_output_format: Literal["json", "json_compact", "markdown"] = "json"
    default_locale: str = "zh-TW"

    # Disclaimer
    disclaimer: str = (
        "⚠️ 免責聲明：本資訊僅供參考，不構成醫療建議。"
        "請諮詢專業醫療人員。"
    )


settings = Settings()

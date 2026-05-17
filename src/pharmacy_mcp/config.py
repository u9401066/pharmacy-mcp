"""MCP Server configuration."""

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_prefix="PHARMACY_MCP_",
        env_file=".env",
        extra="ignore",
    )

    # API URLs
    rxnorm_base_url: str = "https://rxnav.nlm.nih.gov/REST"
    fda_base_url: str = "https://api.fda.gov"
    dailymed_base_url: str = "https://dailymed.nlm.nih.gov/dailymed/services"

    # Cache settings
    cache_dir: str = ".cache"
    cache_ttl_seconds: int = 86400  # 24 hours

    # API settings
    request_timeout: int = 30
    max_retries: int = 3

    # MCP deployment settings
    transport: Literal["stdio", "sse", "streamable-http"] = "stdio"
    host: str = "127.0.0.1"
    port: int = 8000
    mount_path: str = "/"
    streamable_http_path: str = "/mcp"
    stateless_http: bool = False

    # Disclaimer
    disclaimer: str = (
        "This information is for reference, education, and workflow support only. "
        "It does not constitute medical advice and must not be used as the sole "
        "basis for clinical decisions. Consult qualified healthcare professionals "
        "and validated clinical systems for patient care."
    )


settings = Settings()

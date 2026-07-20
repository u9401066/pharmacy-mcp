"""MCP Server configuration."""

from typing import Literal

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
    
    # Cache settings
    cache_dir: str = ".cache"
    cache_ttl_seconds: int = 86400  # 24 hours
    
    # API settings
    request_timeout: int = 30
    max_retries: int = 3
    provider_timeout_seconds: float = 20.0

    # Stable agent-facing response contract
    default_output_format: Literal["json", "json_compact", "markdown"] = "json"
    default_locale: str = "zh-TW"
    
    # Disclaimer
    disclaimer: str = (
        "⚠️ 免責聲明：本資訊僅供參考，不構成醫療建議。"
        "請諮詢專業醫療人員。"
    )


settings = Settings()

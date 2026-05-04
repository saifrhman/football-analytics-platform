"""Runtime settings loaded from environment variables."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings shared by ingestion, API, and dashboard code."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = Field(default="local", alias="ENVIRONMENT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    gcp_project_id: str | None = Field(default=None, alias="GCP_PROJECT_ID")
    gcp_region: str = Field(default="europe-west2", alias="GCP_REGION")
    gcs_bronze_bucket: str | None = Field(default=None, alias="GCS_BRONZE_BUCKET")
    gcs_silver_bucket: str | None = Field(default=None, alias="GCS_SILVER_BUCKET")
    gcs_gold_bucket: str | None = Field(default=None, alias="GCS_GOLD_BUCKET")
    local_bronze_dir: str = Field(default="./data/bronze", alias="LOCAL_BRONZE_DIR")
    local_silver_dir: str = Field(default="./data/silver", alias="LOCAL_SILVER_DIR")
    statsbomb_open_data_base_url: str = Field(
        default="https://raw.githubusercontent.com/statsbomb/open-data/master/data",
        alias="STATSBOMB_OPEN_DATA_BASE_URL",
    )
    statsbomb_local_data_dir: str | None = Field(default=None, alias="STATSBOMB_LOCAL_DATA_DIR")
    statsbomb_bronze_open_data_dir: str = Field(
        default="./data/bronze/statsbomb/open-data",
        alias="STATSBOMB_BRONZE_OPEN_DATA_DIR",
    )
    statsbomb_collections: str = Field(
        default="competitions,matches,events,lineups,three-sixty",
        alias="STATSBOMB_COLLECTIONS",
    )
    statsbomb_competition_ids: str | None = Field(default=None, alias="STATSBOMB_COMPETITION_IDS")
    statsbomb_season_ids: str | None = Field(default=None, alias="STATSBOMB_SEASON_IDS")
    statsbomb_match_ids: str | None = Field(default=None, alias="STATSBOMB_MATCH_IDS")
    transfermarkt_base_url: str = Field(
        default="https://www.transfermarkt.com",
        alias="TRANSFERMARKT_BASE_URL",
    )
    transfermarkt_user_agent: str = Field(
        default="football-intelligence-platform/0.1",
        alias="TRANSFERMARKT_USER_AGENT",
    )
    transfermarkt_request_delay_seconds: float = Field(
        default=2.0,
        alias="TRANSFERMARKT_REQUEST_DELAY_SECONDS",
    )
    transfermarkt_squad_urls: str | None = Field(default=None, alias="TRANSFERMARKT_SQUAD_URLS")
    transfermarkt_transfer_urls: str | None = Field(
        default=None,
        alias="TRANSFERMARKT_TRANSFER_URLS",
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached settings for the current process."""

    return Settings()

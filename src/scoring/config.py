from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "", "case_sensitive": False, "env_file": ".env"}

    # GCP
    gcp_project_id: str
    gcp_region: str = "europe-west1"

    # Gemini
    gemini_model: str = "gemini-2.5-flash"
    gemini_temperature: float = 0.1
    gemini_max_tokens: int = 16384 #65535 default

    # Pub/Sub topic (shared event bus)
    event_bus_topic: str = "carv-events-dev"

    # GCS
    gcs_bucket: str

    # Service identity
    source_service: str = "carv-os-scoring"

    # Observability
    otel_enabled: bool = True


def get_settings() -> Settings:
    return Settings()

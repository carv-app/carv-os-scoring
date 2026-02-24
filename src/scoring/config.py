from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "", "case_sensitive": False}

    # GCP
    gcp_project_id: str
    gcp_region: str = "europe-west1"

    # Gemini
    gemini_model: str = "gemini-2.5-flash"
    gemini_temperature: float = 0.1
    gemini_max_tokens: int = 16384 #65535 default

    # Firestore collections
    scoring_results_collection: str = "scoring_results"

    # Pub/Sub topics (for publishing score events)
    score_calculated_topic: str = "carv.score.calculated"
    score_failed_topic: str = "carv.score.failed"

    # Observability
    otel_enabled: bool = True


def get_settings() -> Settings:
    return Settings()

import os
from contextlib import asynccontextmanager

import structlog
from dotenv import load_dotenv
from fastapi import FastAPI
from google.cloud import pubsub_v1
from google.cloud.firestore import AsyncClient

from scoring.api.routes import router
from scoring.api.scores import router as scores_router
from scoring.config import get_settings
from scoring.observability.setup import init_observability

# Load .env into os.environ so that PUBSUB_EMULATOR_HOST (read directly
# by the google-cloud-pubsub client) and other vars are available before
# any client is constructed.  Existing env vars are NOT overwritten.
load_dotenv()

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ],
)

logger = structlog.get_logger()


def _ensure_emulator_topics(
    client: pubsub_v1.PublisherClient,
    project_id: str,
    topic_names: list[str],
) -> None:
    """Create topics on the Pub/Sub emulator if they don't exist."""
    for name in topic_names:
        topic_path = client.topic_path(project_id, name)
        try:
            client.create_topic(request={"name": topic_path})
            logger.info("emulator_topic_created", topic=name)
        except Exception:
            # Topic already exists — ignore
            pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.settings = settings

    if settings.otel_enabled:
        init_observability(settings)
        logger.info("otel_initialized")

    app.state.firestore_client = AsyncClient(project=settings.gcp_project_id)
    app.state.publisher_client = pubsub_v1.PublisherClient()

    # Auto-create topics when running against the Pub/Sub emulator
    if os.environ.get("PUBSUB_EMULATOR_HOST"):
        _ensure_emulator_topics(
            app.state.publisher_client,
            settings.gcp_project_id,
            [settings.score_calculated_topic, settings.score_failed_topic],
        )
        logger.info(
            "pubsub_emulator_mode",
            host=os.environ["PUBSUB_EMULATOR_HOST"],
        )

    logger.info("clients_initialized", project=settings.gcp_project_id)

    yield

    app.state.firestore_client.close()
    logger.info("shutdown_complete")


app = FastAPI(title="Candidate Scoring Service", lifespan=lifespan)
app.include_router(router)
app.include_router(scores_router)

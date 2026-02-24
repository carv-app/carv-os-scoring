from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from google.cloud import pubsub_v1
from google.cloud.firestore import AsyncClient

from scoring.api.routes import router
from scoring.config import get_settings
from scoring.observability.setup import init_observability

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ],
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.settings = settings

    if settings.otel_enabled:
        init_observability(settings)
        logger.info("otel_initialized")

    app.state.firestore_client = AsyncClient(project=settings.gcp_project_id)
    app.state.publisher_client = pubsub_v1.PublisherClient()
    logger.info("clients_initialized", project=settings.gcp_project_id)

    yield

    app.state.firestore_client.close()
    logger.info("shutdown_complete")


app = FastAPI(title="Candidate Scoring Service", lifespan=lifespan)
app.include_router(router)

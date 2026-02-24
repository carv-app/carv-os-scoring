import base64
import json

import structlog
from fastapi import APIRouter, Depends, HTTPException

from scoring.api.dependencies import get_scoring_service
from scoring.models import ApplicationEventData, PubSubEnvelope, UATSEvent
from scoring.services.scoring import ScoringService

logger = structlog.get_logger()
router = APIRouter()


@router.post("/process-candidate")
async def process_candidate(
    envelope: PubSubEnvelope,
    scoring_service: ScoringService = Depends(get_scoring_service),
):
    # Decode Pub/Sub push → UATS event envelope
    try:
        raw = base64.b64decode(envelope.message.data)
        event = UATSEvent(**json.loads(raw))
        app_data = ApplicationEventData(**event.data)
    except Exception as e:
        logger.error("invalid_event_message", error=str(e))
        # Return 200 for malformed messages — retrying won't fix bad data
        return {"status": "skipped", "reason": "invalid message format"}

    try:
        result = await scoring_service.process(
            application_id=app_data.id,
            candidate_id=app_data.candidate_id,
            vacancy_id=app_data.vacancy_id,
            workspace_id=event.workspace_id,
        )
        return {"status": "ok", "score": result.score}
    except Exception as e:
        logger.error(
            "processing_failed",
            application_id=app_data.id,
            candidate_id=app_data.candidate_id,
            vacancy_id=app_data.vacancy_id,
            error=str(e),
        )
        # Return 500 so Pub/Sub retries with exponential backoff
        raise HTTPException(status_code=500, detail="Processing failed")


@router.get("/health")
async def health():
    return {"status": "ok"}

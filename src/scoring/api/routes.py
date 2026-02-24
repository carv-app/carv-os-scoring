import base64
import json

import structlog
from fastapi import APIRouter, Depends, HTTPException

from scoring.api.dependencies import get_scoring_service
from scoring.models import ATSCandidateVacancyApplication, PubSubEnvelope, UATSEvent
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
        # Handle data as array (backwards-compat: wrap dict in list)
        raw_items = event.data if isinstance(event.data, list) else [event.data]
        applications = [ATSCandidateVacancyApplication(**item) for item in raw_items]
    except Exception as e:
        logger.error("invalid_event_message", error=str(e))
        # Return 200 for malformed messages — retrying won't fix bad data
        return {"status": "skipped", "reason": "invalid message format"}

    try:
        results = []
        for app_data in applications:
            result = await scoring_service.process(
                application_id=app_data.id,
                candidate_reference_id=app_data.candidate_reference_id,
                vacancy_reference_id=app_data.vacancy_reference_id,
                workspace_id=event.workspace_id,
            )
            results.append({"application_id": app_data.id, "score": result.score})
        return {"status": "ok", "results": results}
    except Exception as e:
        logger.error(
            "processing_failed",
            workspace_id=event.workspace_id,
            error=str(e),
        )
        # Return 500 so Pub/Sub retries with exponential backoff
        raise HTTPException(status_code=500, detail="Processing failed")


@router.get("/health")
async def health():
    return {"status": "ok"}

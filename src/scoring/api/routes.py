import base64
import json

import structlog
from fastapi import APIRouter, Depends, HTTPException

from scoring.api.dependencies import get_scoring_service
from scoring.models import ApplicationUpsertedData, EventAttributes, EventPayload, PubSubEnvelope
from scoring.services.scoring import ScoringService

logger = structlog.get_logger()
router = APIRouter()


@router.post("/process-candidate")
async def process_candidate(
    envelope: PubSubEnvelope,
    scoring_service: ScoringService = Depends(get_scoring_service),
):
    # Parse event attributes
    try:
        attributes = EventAttributes.from_pubsub_attributes(envelope.message.attributes)
    except Exception as e:
        logger.error("invalid_event_attributes", error=str(e))
        return {"status": "skipped", "reason": "invalid event attributes"}

    # Only process successful upsert events
    if attributes.event_type != "uats.application.upserted" or attributes.status != "success":
        logger.info(
            "event_skipped",
            event_type=attributes.event_type,
            status=attributes.status,
        )
        return {"status": "skipped", "reason": "irrelevant event type or status"}

    # Decode payload
    try:
        raw = base64.b64decode(envelope.message.data)
        event_payload = EventPayload(**json.loads(raw))
        upserted = ApplicationUpsertedData(**(event_payload.data or {}))
    except Exception as e:
        logger.error("invalid_event_message", error=str(e))
        return {"status": "skipped", "reason": "invalid message format"}

    # Skip deletion events (after is null)
    if upserted.after is None:
        logger.info("deletion_event_skipped")
        return {"status": "skipped", "reason": "deletion event"}

    after = upserted.after

    # Extract file GCS URIs
    file_uris = []
    if after.files:
        for file_type in ("resume", "cover_letter"):
            file_obj = after.files.get(file_type)
            if file_obj and isinstance(file_obj, dict):
                ext_storage = file_obj.get("external_storage", {})
                gcs_uri = ext_storage.get("gcs_uri")
                if gcs_uri:
                    file_uris.append(gcs_uri)

    try:
        result = await scoring_service.process(
            application_id=after.application_id,
            candidate_reference_id=after.candidate_id,
            vacancy_reference_id=after.vacancy_id,
            workspace_id=attributes.workspace_id,
            file_uris=file_uris or None,
        )
        return {
            "status": "ok",
            "application_id": after.application_id,
            "score": result.score,
            "reasoning": result.reasoning,
        }
    except Exception as e:
        logger.error(
            "processing_failed",
            workspace_id=attributes.workspace_id,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail="Processing failed")


@router.get("/health")
async def health():
    return {"status": "ok"}

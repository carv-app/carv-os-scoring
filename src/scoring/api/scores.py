import structlog
from fastapi import APIRouter, Depends, HTTPException, Query

from scoring.api.dependencies import get_firestore_repo, get_scoring_service
from scoring.models import ScoreRequest
from scoring.repositories.firestore import FirestoreRepository
from scoring.services.scoring import ScoringService

logger = structlog.get_logger()
router = APIRouter()


@router.get("/scores/{application_id}")
async def get_score(
    application_id: str,
    workspace_id: str = Query(...),
    repo: FirestoreRepository = Depends(get_firestore_repo),
):
    try:
        result = await repo.get_scoring_result(workspace_id, application_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Scoring result not found")
    return result.model_dump()


@router.get("/scores")
async def list_scores(
    workspace_id: str = Query(...),
    candidate_id: str | None = Query(default=None),
    vacancy_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    repo: FirestoreRepository = Depends(get_firestore_repo),
):
    results = await repo.query_scoring_results(
        workspace_id=workspace_id,
        candidate_id=candidate_id,
        vacancy_id=vacancy_id,
        limit=limit,
    )
    return {
        "results": [r.model_dump() for r in results],
        "count": len(results),
    }


@router.post("/score")
async def trigger_score(
    body: ScoreRequest,
    scoring_service: ScoringService = Depends(get_scoring_service),
):
    try:
        result = await scoring_service.process(
            application_id=body.application_id,
            candidate_reference_id=body.candidate_reference_id,
            vacancy_reference_id=body.vacancy_reference_id,
            workspace_id=body.workspace_id,
        )
    except Exception as e:
        logger.error("score_trigger_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Scoring failed")
    return result.model_dump()


@router.post("/re-score/{application_id}")
async def re_score(
    application_id: str,
    workspace_id: str = Query(...),
    repo: FirestoreRepository = Depends(get_firestore_repo),
    scoring_service: ScoringService = Depends(get_scoring_service),
):
    try:
        existing = await repo.get_scoring_result(workspace_id, application_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Scoring result not found")

    try:
        result = await scoring_service.process(
            application_id=application_id,
            candidate_reference_id=existing.candidate_id,
            vacancy_reference_id=existing.vacancy_id,
            workspace_id=workspace_id,
        )
    except Exception as e:
        logger.error(
            "re_score_failed",
            application_id=application_id,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail="Re-scoring failed")
    return result.model_dump()

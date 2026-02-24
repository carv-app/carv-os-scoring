import asyncio
import time
from datetime import UTC, datetime

import structlog
from opentelemetry import trace

from scoring.models import (
    ScoreCalculatedEventData,
    ScoreEvent,
    ScoringResult,
)
from scoring.observability.metrics import record_failure, record_scoring
from scoring.repositories.firestore import FirestoreRepository
from scoring.services.llm import LLMService
from scoring.services.publisher import EventPublisher

logger = structlog.get_logger()
tracer = trace.get_tracer(__name__)


class ScoringService:
    def __init__(
        self,
        repo: FirestoreRepository,
        llm: LLMService,
        publisher: EventPublisher,
    ) -> None:
        self._repo = repo
        self._llm = llm
        self._publisher = publisher

    async def process(
        self,
        application_id: str,
        candidate_reference_id: str,
        vacancy_reference_id: str,
        workspace_id: str,
    ) -> ScoringResult:
        with tracer.start_as_current_span("scoring.process") as span:
            span.set_attribute("application_id", application_id)
            span.set_attribute("candidate_reference_id", candidate_reference_id)
            span.set_attribute("vacancy_reference_id", vacancy_reference_id)

            try:
                candidate, vacancy, ats_documents = await asyncio.gather(
                    self._repo.get_candidate(workspace_id, candidate_reference_id),
                    self._repo.get_vacancy(workspace_id, vacancy_reference_id),
                    self._repo.get_ats_documents(workspace_id, candidate_reference_id),
                )

                start = time.monotonic()
                llm_response, token_usage = await self._llm.score_candidate(
                    candidate, vacancy, ats_documents
                )
                latency_ms = int((time.monotonic() - start) * 1000)

                now = datetime.now(UTC)

                result = ScoringResult(
                    application_id=application_id,
                    candidate_id=candidate_reference_id,
                    vacancy_id=vacancy_reference_id,
                    workspace_id=workspace_id,
                    score=llm_response.score,
                    reasoning=llm_response.reasoning,
                    model=self._llm._settings.gemini_model,
                    latency_ms=latency_ms,
                    tokens=token_usage,
                    scored_at=now,
                )

                await self._repo.save_scoring_result(result)

                # Publish carv.score.calculated event
                score_data = ScoreCalculatedEventData(
                    application_id=application_id,
                    candidate_id=candidate_reference_id,
                    vacancy_id=vacancy_reference_id,
                    score=result.score,
                    reasoning=result.reasoning,
                    model=result.model,
                )
                event = ScoreEvent(
                    event_name="carv.score.calculated",
                    workspace_id=workspace_id,
                    timestamp=now.isoformat(),
                    data=score_data.model_dump(by_alias=True),
                )
                self._publisher.publish_score_calculated(event.model_dump(by_alias=True))

                record_scoring(result, latency_ms)

                logger.info(
                    "candidate_scored",
                    application_id=application_id,
                    candidate_reference_id=candidate_reference_id,
                    vacancy_reference_id=vacancy_reference_id,
                    score=result.score,
                    latency_ms=latency_ms,
                )

                return result

            except Exception as e:
                record_failure(type(e).__name__)
                logger.error(
                    "scoring_failed",
                    application_id=application_id,
                    candidate_reference_id=candidate_reference_id,
                    vacancy_reference_id=vacancy_reference_id,
                    error=str(e),
                )
                raise

import structlog
from google.cloud.firestore import AsyncClient
from opentelemetry import trace

from scoring.config import Settings
from scoring.models import CandidateDocument, ScoringResult, VacancyDocument

logger = structlog.get_logger()
tracer = trace.get_tracer(__name__)


class FirestoreRepository:
    def __init__(self, client: AsyncClient, settings: Settings) -> None:
        self._client = client
        self._settings = settings

    async def get_candidate(self, candidate_id: str) -> CandidateDocument:
        with tracer.start_as_current_span("firestore.get_candidate"):
            doc = await self._client.collection(
                self._settings.candidates_collection
            ).document(candidate_id).get()
            if not doc.exists:
                raise ValueError(f"Candidate {candidate_id} not found")
            return CandidateDocument(**doc.to_dict())

    async def get_vacancy(self, vacancy_id: str) -> VacancyDocument:
        with tracer.start_as_current_span("firestore.get_vacancy"):
            doc = await self._client.collection(
                self._settings.vacancies_collection
            ).document(vacancy_id).get()
            if not doc.exists:
                raise ValueError(f"Vacancy {vacancy_id} not found")
            return VacancyDocument(**doc.to_dict())

    async def save_scoring_result(self, result: ScoringResult) -> str:
        with tracer.start_as_current_span("firestore.save_result"):
            _, doc_ref = await self._client.collection(
                self._settings.scoring_results_collection
            ).add(result.model_dump())
            logger.info(
                "scoring_result_saved",
                doc_id=doc_ref.id,
                candidate_id=result.candidate_id,
                vacancy_id=result.vacancy_id,
                score=result.score,
            )
            return doc_ref.id

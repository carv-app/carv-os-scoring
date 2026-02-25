import structlog
from google.cloud.firestore import AsyncClient
from opentelemetry import trace

from scoring.config import Settings
from scoring.models import ATSCandidate, AtsDocuments, ATSVacancy, ScoringResult

logger = structlog.get_logger()
tracer = trace.get_tracer(__name__)


class FirestoreRepository:
    def __init__(self, client: AsyncClient, settings: Settings) -> None:
        self._client = client
        self._settings = settings

    async def get_candidate(
        self, workspace_id: str, candidate_reference_id: str
    ) -> ATSCandidate:
        with tracer.start_as_current_span("firestore.get_candidate"):
            doc = (
                await self._client.collection("Workspaces")
                .document(workspace_id)
                .collection("Candidates")
                .document(candidate_reference_id)
                .get()
            )
            if not doc.exists:
                raise ValueError(
                    f"Candidate {candidate_reference_id} not found "
                    f"in workspace {workspace_id}"
                )
            return ATSCandidate(**doc.to_dict())

    async def get_vacancy(
        self, workspace_id: str, vacancy_reference_id: str
    ) -> ATSVacancy:
        with tracer.start_as_current_span("firestore.get_vacancy"):
            doc = (
                await self._client.collection("Workspaces")
                .document(workspace_id)
                .collection("ATSVacancies")
                .document(vacancy_reference_id)
                .get()
            )
            if not doc.exists:
                raise ValueError(
                    f"Vacancy {vacancy_reference_id} not found "
                    f"in workspace {workspace_id}"
                )
            return ATSVacancy(**doc.to_dict())

    async def get_ats_documents(
        self, workspace_id: str, candidate_reference_id: str
    ) -> AtsDocuments:
        with tracer.start_as_current_span("firestore.get_ats_documents"):
            docs_ref = (
                self._client.collection("Workspaces")
                .document(workspace_id)
                .collection("Candidate")
                .document(candidate_reference_id)
                .collection("AtsDocuments")
            )
            merged: dict = {}
            async for doc in docs_ref.stream():
                data = doc.to_dict()
                if data:
                    merged.update(data)
            return AtsDocuments(**merged)

    async def save_scoring_result(self, result: ScoringResult) -> str:
        with tracer.start_as_current_span("firestore.save_result"):
            doc_ref = (
                self._client.collection("Workspaces")
                .document(result.workspace_id)
                .collection("CandidateVacancyApplicationScores")
                .document(result.application_id)
            )
            await doc_ref.set(result.model_dump())
            logger.info(
                "scoring_result_saved",
                doc_id=doc_ref.id,
                workspace_id=result.workspace_id,
                application_id=result.application_id,
                candidate_id=result.candidate_id,
                vacancy_id=result.vacancy_id,
                score=result.score,
            )
            return doc_ref.id

    async def get_scoring_result(
        self, workspace_id: str, application_id: str
    ) -> ScoringResult:
        with tracer.start_as_current_span("firestore.get_scoring_result"):
            doc = await (
                self._client.collection("Workspaces")
                .document(workspace_id)
                .collection("CandidateVacancyApplicationScores")
                .document(application_id)
                .get()
            )
            if not doc.exists:
                raise ValueError(
                    f"Scoring result for application {application_id} "
                    f"not found in workspace {workspace_id}"
                )
            return ScoringResult(**doc.to_dict())

    async def query_scoring_results(
        self,
        workspace_id: str,
        candidate_id: str | None = None,
        vacancy_id: str | None = None,
        limit: int = 50,
    ) -> list[ScoringResult]:
        with tracer.start_as_current_span("firestore.query_scoring_results"):
            query = (
                self._client.collection("Workspaces")
                .document(workspace_id)
                .collection("CandidateVacancyApplicationScores")
            )
            if candidate_id:
                query = query.where("candidate_id", "==", candidate_id)
            if vacancy_id:
                query = query.where("vacancy_id", "==", vacancy_id)
            query = query.order_by("scored_at", direction="DESCENDING").limit(limit)

            results = []
            async for doc in query.stream():
                results.append(ScoringResult(**doc.to_dict()))
            return results

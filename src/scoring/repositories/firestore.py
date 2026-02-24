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

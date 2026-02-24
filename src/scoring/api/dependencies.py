from fastapi import Request

from scoring.repositories.firestore import FirestoreRepository
from scoring.services.llm import LLMService
from scoring.services.publisher import EventPublisher
from scoring.services.scoring import ScoringService


def get_scoring_service(request: Request) -> ScoringService:
    return ScoringService(
        repo=FirestoreRepository(
            client=request.app.state.firestore_client,
            settings=request.app.state.settings,
        ),
        llm=LLMService(settings=request.app.state.settings),
        publisher=EventPublisher(
            client=request.app.state.publisher_client,
            settings=request.app.state.settings,
        ),
    )

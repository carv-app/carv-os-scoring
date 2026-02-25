from fastapi import Request

from scoring.repositories.firestore import FirestoreRepository
from scoring.services.llm import LLMService
from scoring.services.publisher import EventPublisher
from scoring.services.scoring import ScoringService


def get_firestore_repo(request: Request) -> FirestoreRepository:
    return FirestoreRepository(
        client=request.app.state.firestore_client,
        settings=request.app.state.settings,
    )


def get_scoring_service(request: Request) -> ScoringService:
    return ScoringService(
        repo=get_firestore_repo(request),
        llm=LLMService(settings=request.app.state.settings),
        publisher=EventPublisher(
            client=request.app.state.publisher_client,
            settings=request.app.state.settings,
        ),
    )

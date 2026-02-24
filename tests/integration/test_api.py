import base64
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from scoring.models import LLMScoringResponse, ScoringResult


def _make_envelope(
    candidate_id: str = "cand-1",
    vacancy_id: str = "vac-1",
    workspace_id: str = "ws-1",
) -> dict:
    event = {
        "eventName": "uats.application.created",
        "workspaceId": workspace_id,
        "integrationId": "test-integration",
        "timestamp": "2025-01-01T00:00:00Z",
        "data": {
            "id": f"app-{candidate_id}-{vacancy_id}",
            "candidateId": candidate_id,
            "vacancyId": vacancy_id,
        },
    }
    data = base64.b64encode(json.dumps(event).encode()).decode()
    return {
        "message": {
            "data": data,
            "attributes": {},
            "messageId": "msg-123",
            "publishTime": "2025-01-01T00:00:00Z",
        },
        "subscription": "projects/test/subscriptions/test-sub",
    }


@pytest.fixture
def client(settings):
    from scoring.main import app

    app.state.settings = settings
    app.state.firestore_client = AsyncMock()
    app.state.publisher_client = MagicMock()

    return TestClient(app, raise_server_exceptions=False)


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_process_candidate_success(client, sample_candidate, sample_vacancy, settings):
    mock_repo = AsyncMock()
    mock_repo.get_candidate.return_value = sample_candidate
    mock_repo.get_vacancy.return_value = sample_vacancy
    mock_repo.save_scoring_result.return_value = "doc-123"

    mock_llm = AsyncMock()
    mock_llm._settings = settings
    mock_llm.score_candidate.return_value = (
        LLMScoringResponse(score=72, reasoning="Good fit overall."),
        {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120},
    )

    mock_publisher = MagicMock()
    mock_publisher.publish_score_calculated.return_value = "msg-out"

    with patch("scoring.api.dependencies.FirestoreRepository", return_value=mock_repo), patch(
        "scoring.api.dependencies.LLMService", return_value=mock_llm
    ), patch(
        "scoring.api.dependencies.EventPublisher", return_value=mock_publisher
    ), patch("scoring.services.scoring.record_scoring"), patch(
        "scoring.services.scoring.record_failure"
    ):
        response = client.post("/process-candidate", json=_make_envelope())

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["score"] == 72


def test_process_candidate_failure_returns_500(client, settings):
    mock_repo = AsyncMock()
    mock_repo.get_candidate.side_effect = ValueError("Not found")

    with patch("scoring.api.dependencies.FirestoreRepository", return_value=mock_repo), patch(
        "scoring.api.dependencies.LLMService", return_value=AsyncMock()
    ), patch(
        "scoring.api.dependencies.EventPublisher", return_value=MagicMock()
    ), patch("scoring.services.scoring.record_scoring"), patch(
        "scoring.services.scoring.record_failure"
    ):
        response = client.post("/process-candidate", json=_make_envelope())

    assert response.status_code == 500


def test_process_candidate_invalid_message(client):
    envelope = {
        "message": {
            "data": base64.b64encode(b"not json").decode(),
            "attributes": {},
            "messageId": "msg-bad",
            "publishTime": "2025-01-01T00:00:00Z",
        },
        "subscription": "projects/test/subscriptions/test-sub",
    }
    response = client.post("/process-candidate", json=envelope)
    # Invalid messages return 200 (ack) — retrying won't fix bad data
    assert response.status_code == 200
    assert response.json()["status"] == "skipped"

import base64
import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from scoring.models import LLMScoringResponse


def _make_envelope(
    application_id: str = "app-1",
    candidate_id: str = "cand-1",
    vacancy_id: str = "vac-1",
    workspace_id: str = "ws-1",
    event_type: str = "uats.application.upserted",
    status: str = "success",
    after: dict | None = None,
) -> dict:
    if after is None:
        after = {
            "application_id": application_id,
            "candidate_id": candidate_id,
            "vacancy_id": vacancy_id,
        }
    payload = {"data": {"before": None, "after": after}, "error": None}
    data = base64.b64encode(json.dumps(payload).encode()).decode()
    now = datetime.now(UTC).isoformat()
    return {
        "message": {
            "data": data,
            "attributes": {
                "event_id": str(uuid4()),
                "event_type": event_type,
                "status": status,
                "workspace_id": workspace_id,
                "timestamp": now,
                "source_service": "uats",
            },
            "messageId": "msg-123",
            "publishTime": now,
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


def test_process_candidate_success(
    client, sample_candidate, sample_vacancy, sample_ats_documents, settings
):
    mock_repo = AsyncMock()
    mock_repo.get_candidate.return_value = sample_candidate
    mock_repo.get_vacancy.return_value = sample_vacancy
    mock_repo.get_ats_documents.return_value = sample_ats_documents
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
    body = response.json()
    assert body["status"] == "ok"
    assert body["score"] == 72


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
            "attributes": {
                "event_id": str(uuid4()),
                "event_type": "uats.application.upserted",
                "status": "success",
                "workspace_id": "ws-1",
                "timestamp": datetime.now(UTC).isoformat(),
                "source_service": "uats",
            },
            "messageId": "msg-bad",
            "publishTime": "2025-01-01T00:00:00Z",
        },
        "subscription": "projects/test/subscriptions/test-sub",
    }
    response = client.post("/process-candidate", json=envelope)
    assert response.status_code == 200
    assert response.json()["status"] == "skipped"


def test_process_candidate_invalid_attributes(client):
    """Missing or invalid attributes should be skipped."""
    envelope = {
        "message": {
            "data": base64.b64encode(b"{}").decode(),
            "attributes": {"event_type": "uats.application.upserted"},
            "messageId": "msg-bad-attrs",
            "publishTime": "2025-01-01T00:00:00Z",
        },
        "subscription": "projects/test/subscriptions/test-sub",
    }
    response = client.post("/process-candidate", json=envelope)
    assert response.status_code == 200
    assert response.json()["status"] == "skipped"
    assert "attributes" in response.json()["reason"]


def test_process_candidate_deletion_event(client):
    """Deletion events (after=null) should be skipped."""
    envelope = _make_envelope(after=None)
    # Override the payload to have after=null
    payload = {
        "data": {
            "before": {"application_id": "a", "candidate_id": "c", "vacancy_id": "v"},
            "after": None,
        },
        "error": None,
    }
    envelope["message"]["data"] = base64.b64encode(json.dumps(payload).encode()).decode()

    response = client.post("/process-candidate", json=envelope)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "skipped"
    assert body["reason"] == "deletion event"


def test_process_candidate_failure_status_skipped(client):
    """Events with status=failure should be skipped."""
    envelope = _make_envelope(status="failure")
    response = client.post("/process-candidate", json=envelope)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "skipped"
    assert "status" in body["reason"]


def test_process_candidate_wrong_event_type_skipped(client):
    """Events with wrong event_type should be skipped."""
    envelope = _make_envelope(event_type="uats.application.deleted")
    response = client.post("/process-candidate", json=envelope)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "skipped"


def test_process_candidate_with_file_uris(
    client, sample_candidate, sample_vacancy, sample_ats_documents, settings
):
    """File URIs from the event should be passed through to scoring."""
    mock_repo = AsyncMock()
    mock_repo.get_candidate.return_value = sample_candidate
    mock_repo.get_vacancy.return_value = sample_vacancy
    mock_repo.get_ats_documents.return_value = sample_ats_documents
    mock_repo.save_scoring_result.return_value = "doc-123"

    mock_llm = AsyncMock()
    mock_llm._settings = settings
    mock_llm.score_candidate.return_value = (
        LLMScoringResponse(score=80, reasoning="Strong match."),
        {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120},
    )

    mock_publisher = MagicMock()
    mock_publisher.publish_score_calculated.return_value = "msg-out"

    after_with_files = {
        "application_id": "app-1",
        "candidate_id": "cand-1",
        "vacancy_id": "vac-1",
        "files": {
            "resume": {
                "external_storage": {"gcs_uri": "gs://bucket/resume.pdf"}
            },
            "cover_letter": {
                "external_storage": {"gcs_uri": "gs://bucket/cover.pdf"}
            },
        },
    }

    envelope = _make_envelope(after=after_with_files)

    with patch("scoring.api.dependencies.FirestoreRepository", return_value=mock_repo), patch(
        "scoring.api.dependencies.LLMService", return_value=mock_llm
    ), patch(
        "scoring.api.dependencies.EventPublisher", return_value=mock_publisher
    ), patch("scoring.services.scoring.record_scoring"), patch(
        "scoring.services.scoring.record_failure"
    ):
        response = client.post("/process-candidate", json=envelope)

    assert response.status_code == 200
    assert response.json()["status"] == "ok"

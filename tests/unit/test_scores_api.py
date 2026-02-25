from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from scoring.models import LLMScoringResponse, ScoringResult


def _make_scoring_result(**overrides) -> ScoringResult:
    defaults = dict(
        application_id="app-1",
        candidate_id="cand-1",
        vacancy_id="vac-1",
        workspace_id="ws-1",
        score=72,
        reasoning="Good fit overall.",
        model="gemini-2.5-flash",
        latency_ms=1500,
        tokens={"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120},
        scored_at=datetime(2025, 1, 1, tzinfo=UTC),
    )
    defaults.update(overrides)
    return ScoringResult(**defaults)


@pytest.fixture
def client(settings):
    from scoring.main import app

    app.state.settings = settings
    app.state.firestore_client = AsyncMock()
    app.state.publisher_client = MagicMock()

    return TestClient(app, raise_server_exceptions=False)


# --- GET /scores/{application_id} ---


def test_get_score_success(client):
    result = _make_scoring_result()
    mock_repo = AsyncMock()
    mock_repo.get_scoring_result.return_value = result

    with patch("scoring.api.dependencies.FirestoreRepository", return_value=mock_repo):
        response = client.get("/scores/app-1?workspace_id=ws-1")

    assert response.status_code == 200
    body = response.json()
    assert body["candidate_id"] == "cand-1"
    assert body["vacancy_id"] == "vac-1"
    assert body["score"] == 72
    mock_repo.get_scoring_result.assert_awaited_once_with("ws-1", "app-1")


def test_get_score_not_found(client):
    mock_repo = AsyncMock()
    mock_repo.get_scoring_result.side_effect = ValueError("Not found")

    with patch("scoring.api.dependencies.FirestoreRepository", return_value=mock_repo):
        response = client.get("/scores/app-1?workspace_id=ws-1")

    assert response.status_code == 404


def test_get_score_missing_workspace_id(client):
    response = client.get("/scores/app-1")
    assert response.status_code == 422


# --- GET /scores ---


def test_list_scores(client):
    results = [
        _make_scoring_result(candidate_id="cand-1"),
        _make_scoring_result(candidate_id="cand-2", score=55),
    ]
    mock_repo = AsyncMock()
    mock_repo.query_scoring_results.return_value = results

    with patch("scoring.api.dependencies.FirestoreRepository", return_value=mock_repo):
        response = client.get("/scores?workspace_id=ws-1")

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 2
    assert len(body["results"]) == 2


def test_list_scores_with_filters(client):
    mock_repo = AsyncMock()
    mock_repo.query_scoring_results.return_value = []

    with patch("scoring.api.dependencies.FirestoreRepository", return_value=mock_repo):
        response = client.get(
            "/scores?workspace_id=ws-1&candidate_id=cand-1&vacancy_id=vac-1&limit=10"
        )

    assert response.status_code == 200
    mock_repo.query_scoring_results.assert_awaited_once_with(
        workspace_id="ws-1",
        candidate_id="cand-1",
        vacancy_id="vac-1",
        limit=10,
    )


def test_list_scores_missing_workspace_id(client):
    response = client.get("/scores")
    assert response.status_code == 422


# --- POST /score ---


def test_trigger_score(client, settings):
    mock_repo = AsyncMock()
    mock_repo.save_scoring_result.return_value = "app-1"
    mock_repo.get_candidate.return_value = MagicMock()
    mock_repo.get_vacancy.return_value = MagicMock()
    mock_repo.get_ats_documents.return_value = MagicMock()

    mock_llm = AsyncMock()
    mock_llm._settings = settings
    mock_llm.score_candidate.return_value = (
        LLMScoringResponse(score=72, reasoning="Good fit overall."),
        {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120},
    )

    mock_publisher = MagicMock()

    with patch(
        "scoring.api.dependencies.FirestoreRepository", return_value=mock_repo
    ), patch("scoring.api.dependencies.LLMService", return_value=mock_llm), patch(
        "scoring.api.dependencies.EventPublisher", return_value=mock_publisher
    ), patch("scoring.services.scoring.record_scoring"), patch(
        "scoring.services.scoring.record_failure"
    ):
        response = client.post(
            "/score",
            json={
                "workspace_id": "ws-1",
                "candidate_reference_id": "cand-1",
                "vacancy_reference_id": "vac-1",
                "application_id": "app-1",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["score"] == 72
    assert body["application_id"] == "app-1"


def test_trigger_score_requires_application_id(client):
    response = client.post(
        "/score",
        json={
            "workspace_id": "ws-1",
            "candidate_reference_id": "cand-1",
            "vacancy_reference_id": "vac-1",
        },
    )
    assert response.status_code == 422


def test_trigger_score_failure(client):
    mock_repo = AsyncMock()
    mock_repo.get_candidate.side_effect = ValueError("Not found")

    with patch(
        "scoring.api.dependencies.FirestoreRepository", return_value=mock_repo
    ), patch("scoring.api.dependencies.LLMService", return_value=AsyncMock()), patch(
        "scoring.api.dependencies.EventPublisher", return_value=MagicMock()
    ), patch("scoring.services.scoring.record_scoring"), patch(
        "scoring.services.scoring.record_failure"
    ):
        response = client.post(
            "/score",
            json={
                "workspace_id": "ws-1",
                "candidate_reference_id": "bad-id",
                "vacancy_reference_id": "vac-1",
                "application_id": "app-1",
            },
        )

    assert response.status_code == 500


# --- POST /re-score/{application_id} ---


def test_re_score_success(client, settings):
    existing = _make_scoring_result()
    mock_repo = AsyncMock()
    mock_repo.get_scoring_result.return_value = existing
    mock_repo.save_scoring_result.return_value = "app-1"
    mock_repo.get_candidate.return_value = MagicMock()
    mock_repo.get_vacancy.return_value = MagicMock()
    mock_repo.get_ats_documents.return_value = MagicMock()

    mock_llm = AsyncMock()
    mock_llm._settings = settings
    mock_llm.score_candidate.return_value = (
        LLMScoringResponse(score=80, reasoning="Better fit on re-evaluation."),
        {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120},
    )

    mock_publisher = MagicMock()

    with patch(
        "scoring.api.dependencies.FirestoreRepository", return_value=mock_repo
    ), patch("scoring.api.dependencies.LLMService", return_value=mock_llm), patch(
        "scoring.api.dependencies.EventPublisher", return_value=mock_publisher
    ), patch("scoring.services.scoring.record_scoring"), patch(
        "scoring.services.scoring.record_failure"
    ):
        response = client.post("/re-score/app-1?workspace_id=ws-1")

    assert response.status_code == 200
    body = response.json()
    assert body["score"] == 80
    mock_repo.get_scoring_result.assert_awaited_once_with("ws-1", "app-1")


def test_re_score_not_found(client):
    mock_repo = AsyncMock()
    mock_repo.get_scoring_result.side_effect = ValueError("Not found")

    with patch(
        "scoring.api.dependencies.FirestoreRepository", return_value=mock_repo
    ), patch("scoring.api.dependencies.LLMService", return_value=AsyncMock()), patch(
        "scoring.api.dependencies.EventPublisher", return_value=MagicMock()
    ):
        response = client.post("/re-score/app-1?workspace_id=ws-1")

    assert response.status_code == 404

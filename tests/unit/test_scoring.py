from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from scoring.models import LLMScoringResponse, ScoringResult
from scoring.services.scoring import ScoringService


@pytest.fixture
def mock_repo(sample_candidate, sample_vacancy):
    repo = AsyncMock()
    repo.get_candidate.return_value = sample_candidate
    repo.get_vacancy.return_value = sample_vacancy
    repo.save_scoring_result.return_value = "doc-123"
    return repo


@pytest.fixture
def mock_llm(settings):
    llm = AsyncMock()
    llm._settings = settings
    llm.score_candidate.return_value = (
        LLMScoringResponse(score=65, reasoning="Moderate fit due to field mismatch."),
        {"prompt_tokens": 500, "completion_tokens": 50, "total_tokens": 550},
    )
    return llm


@pytest.fixture
def mock_publisher():
    publisher = MagicMock()
    publisher.publish_score_calculated.return_value = "msg-123"
    return publisher


@pytest.mark.asyncio
async def test_process_success(mock_repo, mock_llm, mock_publisher):
    service = ScoringService(repo=mock_repo, llm=mock_llm, publisher=mock_publisher)

    with patch("scoring.services.scoring.record_scoring"), patch(
        "scoring.services.scoring.record_failure"
    ):
        result = await service.process("app-1", "cand-1", "vac-1", "ws-1")

    assert isinstance(result, ScoringResult)
    assert result.score == 65
    assert result.application_id == "app-1"
    assert result.candidate_id == "cand-1"
    assert result.vacancy_id == "vac-1"
    assert result.workspace_id == "ws-1"
    assert result.reasoning == "Moderate fit due to field mismatch."

    mock_repo.get_candidate.assert_awaited_once_with("cand-1")
    mock_repo.get_vacancy.assert_awaited_once_with("vac-1")
    mock_llm.score_candidate.assert_awaited_once()
    mock_repo.save_scoring_result.assert_awaited_once()
    mock_publisher.publish_score_calculated.assert_called_once()


@pytest.mark.asyncio
async def test_process_firestore_error(mock_repo, mock_llm, mock_publisher):
    mock_repo.get_candidate.side_effect = ValueError("Candidate not found")
    service = ScoringService(repo=mock_repo, llm=mock_llm, publisher=mock_publisher)

    with patch("scoring.services.scoring.record_scoring"), patch(
        "scoring.services.scoring.record_failure"
    ), pytest.raises(ValueError, match="Candidate not found"):
        await service.process("app-1", "bad-id", "vac-1", "ws-1")

    mock_llm.score_candidate.assert_not_awaited()
    mock_publisher.publish_score_calculated.assert_not_called()


@pytest.mark.asyncio
async def test_process_llm_error(mock_repo, mock_llm, mock_publisher):
    mock_llm.score_candidate.side_effect = RuntimeError("Gemini timeout")
    service = ScoringService(repo=mock_repo, llm=mock_llm, publisher=mock_publisher)

    with patch("scoring.services.scoring.record_scoring"), patch(
        "scoring.services.scoring.record_failure"
    ), pytest.raises(RuntimeError, match="Gemini timeout"):
        await service.process("app-1", "cand-1", "vac-1", "ws-1")

    mock_repo.save_scoring_result.assert_not_awaited()
    mock_publisher.publish_score_calculated.assert_not_called()

from scoring.models import LLMScoringResponse


def test_llm_scoring_response_valid():
    response = LLMScoringResponse(score=75, reasoning="Good fit for the role.")
    assert response.score == 75
    assert response.reasoning == "Good fit for the role."


def test_llm_scoring_response_boundary_values():
    low = LLMScoringResponse(score=0, reasoning="Poor fit.")
    assert low.score == 0

    high = LLMScoringResponse(score=100, reasoning="Perfect fit.")
    assert high.score == 100


def test_llm_scoring_response_from_json():
    raw = '{"score": 42, "reasoning": "Moderate fit with some gaps."}'
    response = LLMScoringResponse.model_validate_json(raw)
    assert response.score == 42
    assert "Moderate fit" in response.reasoning


def test_llm_scoring_response_rejects_invalid_score():
    import pytest

    with pytest.raises(Exception):
        LLMScoringResponse(score=101, reasoning="Too high")

    with pytest.raises(Exception):
        LLMScoringResponse(score=-1, reasoning="Too low")

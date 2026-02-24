from scoring.models import CandidateDocument, CandidateSource, VacancyDocument
from scoring.services.prompt import SYSTEM_PROMPT, build_user_prompt


def test_system_prompt_contains_scoring_rubric():
    assert "90-100" in SYSTEM_PROMPT
    assert "0-29" in SYSTEM_PROMPT
    assert "English" in SYSTEM_PROMPT


def test_build_user_prompt_includes_candidate_and_vacancy(sample_candidate, sample_vacancy):
    prompt = build_user_prompt(sample_candidate, sample_vacancy)

    assert "Thomas van den Berg-Smit" in prompt
    assert "Source: CV" in prompt
    assert "HBO Verpleegkunde" in prompt
    assert "Source: Interview" in prompt
    assert "Tandartsassistent" in prompt


def test_build_user_prompt_handles_empty_sources(sample_vacancy):
    candidate = CandidateDocument(name="Test", sources=[])
    prompt = build_user_prompt(candidate, sample_vacancy)

    assert "Test" in prompt
    assert "Vacancy Description" in prompt


def test_build_user_prompt_handles_no_name(sample_vacancy):
    candidate = CandidateDocument(
        sources=[
            CandidateSource(
                source_label="Note",
                source_content="Some content",
                source_metadata={},
            )
        ]
    )
    prompt = build_user_prompt(candidate, sample_vacancy)

    assert "Source: Note" in prompt
    assert "Some content" in prompt

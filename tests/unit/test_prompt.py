from scoring.models import ATSCandidate, AtsDocuments, ATSVacancy, ATSVacancyAddress
from scoring.services.prompt import SYSTEM_PROMPT, build_user_prompt


def test_system_prompt_contains_scoring_rubric():
    assert "90-100" in SYSTEM_PROMPT
    assert "0-29" in SYSTEM_PROMPT
    assert "English" in SYSTEM_PROMPT


def test_build_user_prompt_includes_candidate_and_vacancy(
    sample_candidate, sample_vacancy, sample_ats_documents
):
    prompt = build_user_prompt(sample_candidate, sample_vacancy, sample_ats_documents)

    assert "Thomas van den Berg-Smit" in prompt
    assert "thomas@example.com" in prompt
    assert "Verpleegkundige" in prompt
    assert "Zorggroep West" in prompt
    assert "HBO Verpleegkunde" in prompt
    assert "Tandartsassistent" in prompt
    assert "BIG registratie" in prompt
    assert "Teamplayer" in prompt


def test_build_user_prompt_includes_documents(sample_candidate, sample_vacancy):
    docs = AtsDocuments(
        resume="Some resume content",
        job_description="Some job description",
        assessment="Assessment results",
    )
    prompt = build_user_prompt(sample_candidate, sample_vacancy, docs)

    assert "### Resume" in prompt
    assert "Some resume content" in prompt
    assert "### Job Description" in prompt
    assert "Some job description" in prompt
    assert "### Assessment" in prompt
    assert "Assessment results" in prompt


def test_build_user_prompt_skips_empty_documents(sample_candidate, sample_vacancy):
    docs = AtsDocuments()
    prompt = build_user_prompt(sample_candidate, sample_vacancy, docs)

    assert "### Resume" not in prompt
    assert "### Job Description" not in prompt
    assert "### Assessment" not in prompt


def test_build_user_prompt_handles_no_name(sample_vacancy, sample_ats_documents):
    candidate = ATSCandidate(firstname="Jan", lastname="de Vries")
    prompt = build_user_prompt(candidate, sample_vacancy, sample_ats_documents)

    assert "Jan de Vries" in prompt


def test_build_user_prompt_handles_minimal_candidate(sample_vacancy):
    candidate = ATSCandidate()
    docs = AtsDocuments()
    prompt = build_user_prompt(candidate, sample_vacancy, docs)

    assert "Vacancy Description" in prompt
    assert "Tandartsassistent" in prompt


def test_build_user_prompt_includes_location(sample_candidate, sample_ats_documents):
    vacancy = ATSVacancy(
        title="Test Role",
        address=ATSVacancyAddress(city="Amsterdam", country="Netherlands"),
    )
    prompt = build_user_prompt(sample_candidate, vacancy, sample_ats_documents)

    assert "Amsterdam" in prompt
    assert "Netherlands" in prompt

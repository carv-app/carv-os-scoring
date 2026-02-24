"""Test that models deserialize correctly from camelCase Firestore data."""

from scoring.models import (
    ATSCandidate,
    ATSCandidateVacancyApplication,
    AtsDocuments,
    ATSVacancy,
)


def test_ats_candidate_from_firestore_data():
    """Firestore returns camelCase keys like profileUrl, workspaceId."""
    data = {
        "id": "aUFe1f8g84GGORCL",
        "name": "Jaward Sally",
        "firstname": "Jaward",
        "lastname": "Sally",
        "email": "jaward@example.com",
        "phone": "+31612345678",
        "address": "",
        "profileUrl": "https://example.com/candidates/123",
        "workspaceId": "ws-123",
    }
    candidate = ATSCandidate(**data)
    assert candidate.name == "Jaward Sally"
    assert candidate.profile_url == "https://example.com/candidates/123"
    assert candidate.workspace_id == "ws-123"


def test_ats_vacancy_from_firestore_data():
    """Firestore returns camelCase keys like hardRequirements, aboutCompany."""
    data = {
        "id": "vac-1",
        "title": "TIG-Lasser",
        "description": "Some description",
        "hardRequirements": "TIG-lascertificaat",
        "softRequirements": "Teamplayer",
        "aboutCompany": "Internationaal bedrijf",
        "address": {
            "address1": "Industrieweg 5",
            "city": "Doetinchem",
            "zip": "7005 AB",
            "country": "Netherlands",
            "countryCode": "NL",
        },
        "status": "open",
        "workspaceId": "ws-123",
    }
    vacancy = ATSVacancy(**data)
    assert vacancy.hard_requirements == "TIG-lascertificaat"
    assert vacancy.soft_requirements == "Teamplayer"
    assert vacancy.about_company == "Internationaal bedrijf"
    assert vacancy.address.street == "Industrieweg 5"
    assert vacancy.address.city == "Doetinchem"
    assert vacancy.address.zip_code == "7005 AB"
    assert vacancy.workspace_id == "ws-123"


def test_ats_vacancy_from_firestore_with_empty_requirements():
    """Real Firestore data often has empty strings for requirements."""
    data = {
        "id": "vac-2",
        "title": "TIG-Lasser",
        "description": "<p>Some HTML</p>",
        "hardRequirements": "",
        "softRequirements": "",
        "aboutCompany": "",
        "address": {"city": "", "country": "Netherlands", "countryCode": "NL"},
        "status": "",
        "workspaceId": "ws-123",
    }
    vacancy = ATSVacancy(**data)
    assert vacancy.hard_requirements == ""
    assert vacancy.about_company == ""


def test_ats_documents_from_firestore_data():
    """AtsDocuments uses jobDescription alias."""
    data = {"resume": "CV content", "jobDescription": "Job desc content"}
    docs = AtsDocuments(**data)
    assert docs.resume == "CV content"
    assert docs.job_description == "Job desc content"
    assert docs.assessment is None


def test_ats_documents_empty():
    """Empty AtsDocuments when subcollection has no docs."""
    docs = AtsDocuments()
    assert docs.resume is None
    assert docs.job_description is None
    assert docs.assessment is None


def test_application_from_event_data():
    """ATSCandidateVacancyApplication from camelCase event data."""
    data = {
        "id": "1910930",
        "candidateReferenceId": "aUFe1f8g84GGORCL",
        "vacancyReferenceId": "aIil3cRwkMsuC-pC",
        "status": "05. Interview",
        "workspaceId": "JSiKKjiSDmZoX7Zfk2qG",
    }
    app = ATSCandidateVacancyApplication(**data)
    assert app.id == "1910930"
    assert app.candidate_reference_id == "aUFe1f8g84GGORCL"
    assert app.vacancy_reference_id == "aIil3cRwkMsuC-pC"
    assert app.workspace_id == "JSiKKjiSDmZoX7Zfk2qG"


def test_ats_vacancy_ignores_unknown_fields():
    """Firestore docs have extra fields (ownerId, dynamicData, etc.)."""
    data = {
        "id": "vac-1",
        "title": "Test",
        "ownerId": "71886",
        "dynamicData": None,
        "transparentFields": None,
        "clientOne": "",
        "accountId": "",
    }
    vacancy = ATSVacancy.model_validate(data)
    assert vacancy.title == "Test"


def test_ats_candidate_ignores_unknown_fields():
    """Firestore candidate docs have extra fields."""
    data = {
        "id": "cand-1",
        "name": "Test User",
        "schemaVersion": 1,
        "gdprStatus": "Consented",
        "integrationConfiguration": {"provider": "OTYS"},
        "externalReferenceId": "ext-123",
        "createdAt": "2025-01-01T00:00:00Z",
    }
    candidate = ATSCandidate.model_validate(data)
    assert candidate.name == "Test User"

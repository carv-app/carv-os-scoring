"""Test that models deserialize correctly from camelCase Firestore data and new event bus format."""

from datetime import UTC, datetime
from uuid import uuid4

from scoring.models import (
    ApplicationUpsertedData,
    ATSCandidate,
    AtsDocuments,
    ATSVacancy,
    EventAttributes,
    ScoreCalculatedData,
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


def test_event_attributes_from_pubsub_attributes():
    eid = str(uuid4())
    now = datetime.now(UTC).isoformat()
    attrs = {
        "event_id": eid,
        "event_type": "uats.application.upserted",
        "status": "success",
        "workspace_id": "ws-1",
        "timestamp": now,
        "source_service": "carv-os-scoring",
    }
    parsed = EventAttributes.from_pubsub_attributes(attrs)
    assert str(parsed.event_id) == eid
    assert parsed.event_type == "uats.application.upserted"
    assert parsed.status == "success"
    assert parsed.workspace_id == "ws-1"
    assert parsed.source_service == "carv-os-scoring"


def test_event_attributes_to_pubsub_attributes():
    eid = uuid4()
    now = datetime.now(UTC)
    attrs = EventAttributes(
        event_id=eid,
        event_type="carv.score.calculated",
        status="success",
        workspace_id="ws-1",
        timestamp=now,
        source_service="carv-os-scoring",
    )
    result = attrs.to_pubsub_attributes()
    assert isinstance(result, dict)
    assert all(isinstance(v, str) for v in result.values())
    assert result["event_id"] == str(eid)
    assert result["event_type"] == "carv.score.calculated"
    assert result["workspace_id"] == "ws-1"


def test_application_upserted_data_parsing():
    data = {
        "before": None,
        "after": {
            "application_id": "app-1",
            "candidate_id": "cand-1",
            "vacancy_id": "vac-1",
            "files": {
                "resume": {
                    "external_storage": {"gcs_uri": "gs://bucket/resume.pdf"}
                }
            },
        },
    }
    upserted = ApplicationUpsertedData(**data)
    assert upserted.before is None
    assert upserted.after is not None
    assert upserted.after.application_id == "app-1"
    assert upserted.after.candidate_id == "cand-1"
    assert upserted.after.vacancy_id == "vac-1"
    assert upserted.after.files["resume"]["external_storage"]["gcs_uri"] == "gs://bucket/resume.pdf"


def test_application_upserted_data_deletion():
    data = {
        "before": {"application_id": "app-1", "candidate_id": "c", "vacancy_id": "v"},
        "after": None,
    }
    upserted = ApplicationUpsertedData(**data)
    assert upserted.after is None
    assert upserted.before is not None


def test_score_calculated_data_snake_case():
    data = ScoreCalculatedData(
        application_id="app-1",
        candidate_id="cand-1",
        vacancy_id="vac-1",
        score=85,
        reasoning="Great fit",
        model="gemini-2.5-flash",
    )
    dumped = data.model_dump()
    assert "application_id" in dumped
    assert "candidate_id" in dumped
    assert "vacancy_id" in dumped
    assert dumped["score"] == 85


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

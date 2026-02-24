import os

import pytest

# Set required env vars before any imports that trigger Settings
os.environ.setdefault("GCP_PROJECT_ID", "test-project")
os.environ.setdefault("GCP_REGION", "europe-west1")
os.environ.setdefault("OTEL_ENABLED", "false")


@pytest.fixture
def settings():
    from scoring.config import Settings

    return Settings(
        gcp_project_id="test-project",
        gcp_region="europe-west1",
        otel_enabled=False,
    )


@pytest.fixture
def sample_candidate():
    from scoring.models import ATSCandidate, CandidateJob

    return ATSCandidate(
        id="cand-1",
        name="Thomas van den Berg-Smit",
        firstname="Thomas",
        lastname="van den Berg-Smit",
        email="thomas@example.com",
        phone="+31612345678",
        address="Amsterdam, Netherlands",
        job=CandidateJob(title="Verpleegkundige", company="Zorggroep West"),
        source="recruiter",
        workspace_id="ws-1",
    )


@pytest.fixture
def sample_vacancy():
    from scoring.models import ATSVacancy, ATSVacancyAddress

    return ATSVacancy(
        id="vac-1",
        title="Tandartsassistent",
        description="Zoek tandartsassistenten voor moderne praktijk in regio Westland.",
        hard_requirements="BIG registratie, MBO4 Tandartsassistent",
        soft_requirements="Teamplayer, communicatief sterk",
        about_company="Moderne tandartspraktijk in het Westland",
        address=ATSVacancyAddress(
            city="Westland",
            country="Netherlands",
        ),
        status="open",
        workspace_id="ws-1",
    )


@pytest.fixture
def sample_ats_documents():
    from scoring.models import AtsDocuments

    return AtsDocuments(
        resume="HBO Verpleegkunde, 6 jaar ervaring in de zorg.",
        job_description="Tandartsassistent gezocht voor 32 uur per week.",
        assessment="Kandidaat zoekt werk in ouderenzorg, beschikbaar per direct.",
    )

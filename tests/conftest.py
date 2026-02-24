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
    from scoring.models import CandidateDocument, CandidateSource

    return CandidateDocument(
        name="Thomas van den Berg-Smit",
        sources=[
            CandidateSource(
                source_label="CV",
                source_content="HBO Verpleegkunde, 6 jaar ervaring in de zorg.",
                source_metadata={"document_type": "CV"},
            ),
            CandidateSource(
                source_label="Interview",
                source_content="Kandidaat zoekt werk in ouderenzorg, beschikbaar per direct.",
                source_metadata={},
            ),
        ],
    )


@pytest.fixture
def sample_vacancy():
    from scoring.models import VacancyDocument

    return VacancyDocument(
        title="Tandartsassistent",
        description="Zoek tandartsassistenten voor moderne praktijk in regio Westland.",
    )

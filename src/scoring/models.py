from datetime import datetime

from pydantic import BaseModel, Field

# --- Pub/Sub push envelope (wraps all events) ---


class PubSubMessage(BaseModel):
    data: str  # base64-encoded JSON
    attributes: dict[str, str] = Field(default_factory=dict)
    message_id: str = Field(alias="messageId", default="")
    publish_time: str = Field(alias="publishTime", default="")


class PubSubEnvelope(BaseModel):
    message: PubSubMessage
    subscription: str = ""


# --- UATS event models ---


class ATSCandidateVacancyApplication(BaseModel):
    id: str
    candidate_reference_id: str = Field(alias="candidateReferenceId")
    vacancy_reference_id: str = Field(alias="vacancyReferenceId")
    status: str = ""
    workspace_id: str = Field(alias="workspaceId", default="")

    model_config = {"populate_by_name": True}


class UATSEvent(BaseModel):
    event_name: str = Field(alias="eventName")
    workspace_id: str = Field(alias="workspaceId")
    integration_id: str = Field(alias="integrationId", default="")
    timestamp: str = ""
    data: dict | list = Field(default_factory=dict)

    model_config = {"populate_by_name": True}


# --- Score event (published by this service) ---


class ScoreCalculatedEventData(BaseModel):
    application_id: str = Field(serialization_alias="applicationId")
    candidate_id: str = Field(serialization_alias="candidateId")
    vacancy_id: str = Field(serialization_alias="vacancyId")
    score: int
    reasoning: str
    model: str

    model_config = {"populate_by_name": True}


class ScoreEvent(BaseModel):
    event_name: str = Field(serialization_alias="eventName")
    workspace_id: str = Field(serialization_alias="workspaceId")
    timestamp: str
    data: dict

    model_config = {"populate_by_name": True}


# --- Firestore ATS document models ---


class CandidateJob(BaseModel):
    title: str = ""
    company: str = ""


class ATSCandidate(BaseModel):
    id: str = ""
    name: str = ""
    firstname: str = ""
    lastname: str = ""
    email: str = ""
    phone: str = ""
    address: str = ""
    job: CandidateJob = Field(default_factory=CandidateJob)
    source: str = ""
    profile_url: str = Field(alias="profileUrl", default="")
    resume_url: str = Field(alias="resumeUrl", default="")
    workspace_id: str = Field(alias="workspaceId", default="")

    model_config = {"populate_by_name": True}


class ATSVacancyAddress(BaseModel):
    street: str = Field(alias="address1", default="")
    city: str = ""
    zip_code: str = Field(alias="zip", default="")
    country: str = ""

    model_config = {"populate_by_name": True}


class ATSVacancy(BaseModel):
    id: str = ""
    title: str = ""
    description: str = ""
    hard_requirements: str = Field(alias="hardRequirements", default="")
    soft_requirements: str = Field(alias="softRequirements", default="")
    about_company: str = Field(alias="aboutCompany", default="")
    address: ATSVacancyAddress = Field(default_factory=ATSVacancyAddress)
    status: str = ""
    workspace_id: str = Field(alias="workspaceId", default="")

    model_config = {"populate_by_name": True}


class AtsDocuments(BaseModel):
    resume: str | None = None
    job_description: str | None = Field(alias="jobDescription", default=None)
    assessment: str | None = None

    model_config = {"populate_by_name": True}


# --- LLM response ---


class LLMScoringResponse(BaseModel):
    score: int = Field(ge=0, le=100)
    reasoning: str


# --- Scoring result ---


class ScoringResult(BaseModel):
    application_id: str
    candidate_id: str
    vacancy_id: str
    workspace_id: str
    score: int = Field(ge=0, le=100)
    reasoning: str
    model: str
    latency_ms: int
    tokens: dict = Field(default_factory=dict)
    scored_at: datetime = Field(default_factory=datetime.utcnow)

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

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


# --- Event bus models (new format) ---


class EventAttributes(BaseModel):
    event_id: UUID
    event_type: str
    status: Literal["success", "failure"]
    workspace_id: str
    timestamp: datetime
    source_service: str

    def to_pubsub_attributes(self) -> dict[str, str]:
        return {k: str(v) for k, v in self.model_dump(mode="json").items()}

    @classmethod
    def from_pubsub_attributes(cls, attrs: dict[str, str]) -> "EventAttributes":
        return cls.model_validate(attrs)


class EventPayload(BaseModel):
    data: dict[str, Any] | None = None
    error: dict[str, Any] | None = None


# --- Incoming application models ---


class ApplicationSnapshot(BaseModel):
    application_id: str
    candidate_id: str
    vacancy_id: str
    files: dict[str, Any] | None = None
    created_at: str = ""
    updated_at: str = ""


class ApplicationUpsertedData(BaseModel):
    before: ApplicationSnapshot | None = None
    after: ApplicationSnapshot | None = None


# --- Outgoing score event data (snake_case) ---


class ScoreCalculatedData(BaseModel):
    application_id: str
    candidate_id: str
    vacancy_id: str
    score: int
    reasoning: str
    model: str


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


# --- Score request (HTTP API) ---


class ScoreRequest(BaseModel):
    workspace_id: str
    candidate_reference_id: str
    vacancy_reference_id: str
    application_id: str


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

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


class ApplicationEventData(BaseModel):
    id: str = Field(alias="id")
    candidate_id: str = Field(alias="candidateId")
    vacancy_id: str = Field(alias="vacancyId")

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


# --- Firestore document models ---


class CandidateSource(BaseModel):
    source_label: str
    source_content: str
    source_metadata: dict = Field(default_factory=dict)


class CandidateDocument(BaseModel):
    name: str = ""
    sources: list[CandidateSource] = Field(default_factory=list)


class VacancyDocument(BaseModel):
    title: str
    description: str


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

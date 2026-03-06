import json

import structlog
from google.cloud import pubsub_v1
from opentelemetry import trace

from scoring.config import Settings
from scoring.models import EventAttributes, EventPayload

logger = structlog.get_logger()
tracer = trace.get_tracer(__name__)


class EventPublisher:
    def __init__(self, client: pubsub_v1.PublisherClient, settings: Settings) -> None:
        self._client = client
        self._settings = settings

    def _topic_path(self, topic: str) -> str:
        return self._client.topic_path(self._settings.gcp_project_id, topic)

    def publish(self, payload: EventPayload, attributes: EventAttributes) -> str:
        with tracer.start_as_current_span("publisher.publish"):
            future = self._client.publish(
                self._topic_path(self._settings.event_bus_topic),
                data=json.dumps(payload.model_dump(mode="json")).encode("utf-8"),
                ordering_key=attributes.workspace_id,
                **attributes.to_pubsub_attributes(),
            )
            message_id = future.result()
            logger.info(
                "event_published",
                event_type=attributes.event_type,
                message_id=message_id,
            )
            return message_id

import json

import structlog
from google.cloud import pubsub_v1
from opentelemetry import trace

from scoring.config import Settings

logger = structlog.get_logger()
tracer = trace.get_tracer(__name__)


class EventPublisher:
    def __init__(self, client: pubsub_v1.PublisherClient, settings: Settings) -> None:
        self._client = client
        self._settings = settings

    def _topic_path(self, topic: str) -> str:
        return self._client.topic_path(self._settings.gcp_project_id, topic)

    def publish_score_calculated(self, event_data: dict) -> str:
        with tracer.start_as_current_span("publisher.score_calculated"):
            future = self._client.publish(
                self._topic_path(self._settings.score_calculated_topic),
                data=json.dumps(event_data).encode("utf-8"),
            )
            message_id = future.result()
            logger.info("score_calculated_published", message_id=message_id)
            return message_id

    def publish_score_failed(self, event_data: dict) -> str:
        with tracer.start_as_current_span("publisher.score_failed"):
            future = self._client.publish(
                self._topic_path(self._settings.score_failed_topic),
                data=json.dumps(event_data).encode("utf-8"),
            )
            message_id = future.result()
            logger.info("score_failed_published", message_id=message_id)
            return message_id

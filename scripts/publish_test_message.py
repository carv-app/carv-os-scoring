"""Publish a test uats.application.created event to trigger scoring."""

import json
import sys
from datetime import datetime, timezone

from google.cloud import pubsub_v1


def main():
    if len(sys.argv) < 2:
        print(
            "Usage: python publish_test_message.py <gcp-project-id> "
            "[candidate-ref-id] [vacancy-ref-id] [workspace-id]"
        )
        sys.exit(1)

    project_id = sys.argv[1]
    candidate_ref_id = sys.argv[2] if len(sys.argv) > 2 else "candidate-001"
    vacancy_ref_id = sys.argv[3] if len(sys.argv) > 3 else "vacancy-001"
    workspace_id = sys.argv[4] if len(sys.argv) > 4 else "workspace-001"

    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(project_id, "uats.application.created")

    event = {
        "eventName": "uats.application.created",
        "workspaceId": workspace_id,
        "integrationId": "manual-test",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": [
            {
                "id": f"app-{candidate_ref_id}-{vacancy_ref_id}",
                "candidateReferenceId": candidate_ref_id,
                "vacancyReferenceId": vacancy_ref_id,
                "status": "new",
                "workspaceId": workspace_id,
            },
        ],
    }

    message_data = json.dumps(event).encode("utf-8")
    future = publisher.publish(topic_path, data=message_data)
    message_id = future.result()

    print(f"Published message {message_id} to {topic_path}")
    print(f"  event: uats.application.created")
    print(f"  candidateReferenceId: {candidate_ref_id}")
    print(f"  vacancyReferenceId: {vacancy_ref_id}")
    print(f"  workspaceId: {workspace_id}")


if __name__ == "__main__":
    main()

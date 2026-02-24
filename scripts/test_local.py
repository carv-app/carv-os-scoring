"""Test the scoring service locally.

Three modes:
  1. Hardcoded — uses built-in fake data, no GCP auth needed:
       python scripts/test_local.py

  2. From Firestore application — reads a real ATSCandidateVacancyApplication
     and builds the event from it:
       python scripts/test_local.py --application WSiD/AppID
       python scripts/test_local.py --application JSiKKjiSDmZoX7Zfk2qG/1910930

  3. From explicit IDs:
       python scripts/test_local.py --workspace WSiD --candidate CID --vacancy VID

Requires the scoring service to be running locally:
  OTEL_ENABLED=false GCP_PROJECT_ID=carv-app-dev GCP_REGION=europe-west1 \
    uvicorn scoring.main:app --port 8080
"""

import argparse
import base64
import json
import sys
from datetime import UTC, datetime

import requests


def build_envelope(
    application_id: str,
    candidate_reference_id: str,
    vacancy_reference_id: str,
    workspace_id: str,
) -> dict:
    event = {
        "eventName": "uats.application.created",
        "workspaceId": workspace_id,
        "integrationId": "local-test",
        "timestamp": datetime.now(UTC).isoformat(),
        "data": [
            {
                "id": application_id,
                "candidateReferenceId": candidate_reference_id,
                "vacancyReferenceId": vacancy_reference_id,
                "status": "new",
                "workspaceId": workspace_id,
            },
        ],
    }
    return {
        "message": {
            "data": base64.b64encode(json.dumps(event).encode()).decode(),
            "attributes": {},
            "messageId": f"local-{application_id}",
            "publishTime": datetime.now(UTC).isoformat(),
        },
        "subscription": "projects/local/subscriptions/test",
    }


def hardcoded_test(url: str):
    """Send a hardcoded fake event — no GCP auth needed."""
    print("--- Hardcoded test (fake data) ---")
    envelope = build_envelope(
        application_id="app-test-001",
        candidate_reference_id="candidate-001",
        vacancy_reference_id="vacancy-001",
        workspace_id="workspace-001",
    )
    send(url, envelope)


def from_application(url: str, workspace_id: str, application_id: str):
    """Read a real application from Firestore and send it."""
    from google.cloud import firestore

    print(f"--- From Firestore application {workspace_id}/{application_id} ---")
    db = firestore.Client(project="carv-app-dev")
    doc = (
        db.collection("Workspaces")
        .document(workspace_id)
        .collection("ATSCandidateVacancyApplications")
        .document(application_id)
        .get()
    )
    if not doc.exists:
        print(f"Application not found: /Workspaces/{workspace_id}"
              f"/ATSCandidateVacancyApplications/{application_id}")
        sys.exit(1)

    data = doc.to_dict()
    print(f"  candidate: {data.get('candidateReferenceId')}")
    print(f"  vacancy:   {data.get('vacancyReferenceId')}")
    print(f"  status:    {data.get('status')}")

    envelope = build_envelope(
        application_id=data["id"],
        candidate_reference_id=data["candidateReferenceId"],
        vacancy_reference_id=data["vacancyReferenceId"],
        workspace_id=workspace_id,
    )
    send(url, envelope)


def from_ids(
    url: str,
    workspace_id: str,
    candidate_reference_id: str,
    vacancy_reference_id: str,
):
    """Send an event from explicit IDs."""
    print("--- From explicit IDs ---")
    print(f"  workspace: {workspace_id}")
    print(f"  candidate: {candidate_reference_id}")
    print(f"  vacancy:   {vacancy_reference_id}")

    envelope = build_envelope(
        application_id=f"app-{candidate_reference_id}-{vacancy_reference_id}",
        candidate_reference_id=candidate_reference_id,
        vacancy_reference_id=vacancy_reference_id,
        workspace_id=workspace_id,
    )
    send(url, envelope)


def send(url: str, envelope: dict):
    print(f"\nPOST {url}/process-candidate")
    try:
        resp = requests.post(
            f"{url}/process-candidate", json=envelope, timeout=120
        )
    except requests.ConnectionError:
        print("Connection refused — is the server running?")
        print(
            "  OTEL_ENABLED=false GCP_PROJECT_ID=carv-app-dev "
            "GCP_REGION=europe-west1 uvicorn scoring.main:app --port 8080"
        )
        sys.exit(1)

    print(f"Status: {resp.status_code}")
    print(json.dumps(resp.json(), indent=2))


def main():
    parser = argparse.ArgumentParser(
        description="Test the scoring service locally"
    )
    parser.add_argument(
        "--url",
        default="http://localhost:8080",
        help="Base URL of the scoring service (default: http://localhost:8080)",
    )
    parser.add_argument(
        "--application",
        metavar="WORKSPACE_ID/APP_ID",
        help="Read application from Firestore (e.g. JSiKKjiSDmZoX7Zfk2qG/1910930)",
    )
    parser.add_argument("--workspace", help="Workspace ID")
    parser.add_argument("--candidate", help="Candidate reference ID")
    parser.add_argument("--vacancy", help="Vacancy reference ID")
    args = parser.parse_args()

    if args.application:
        parts = args.application.split("/")
        if len(parts) != 2:
            print("--application must be WORKSPACE_ID/APPLICATION_ID")
            sys.exit(1)
        from_application(args.url, parts[0], parts[1])
    elif args.workspace and args.candidate and args.vacancy:
        from_ids(args.url, args.workspace, args.candidate, args.vacancy)
    else:
        hardcoded_test(args.url)


if __name__ == "__main__":
    main()

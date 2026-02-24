"""Seed Firestore with sample candidate and vacancy data in workspace-scoped paths."""

import json
import sys
from pathlib import Path

from google.cloud import firestore

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE_ID = "workspace-001"
CANDIDATE_REFERENCE_ID = "candidate-001"
VACANCY_REFERENCE_ID = "vacancy-001"


def main():
    project_id = sys.argv[1] if len(sys.argv) > 1 else None
    if not project_id:
        print("Usage: python seed_firestore.py <gcp-project-id>")
        sys.exit(1)

    db = firestore.Client(project=project_id)

    # Seed candidate at /Workspaces/{WID}/Candidates/{CID}
    candidate_doc = {
        "id": CANDIDATE_REFERENCE_ID,
        "name": "Thomas Alexander van den Berg-Smit",
        "firstname": "Thomas",
        "lastname": "van den Berg-Smit",
        "email": "thomas@example.com",
        "phone": "+31612345678",
        "address": "Amsterdam, Netherlands",
        "job": {"title": "Verpleegkundige", "company": "Zorggroep West"},
        "source": "recruiter",
        "workspace_id": WORKSPACE_ID,
    }
    (
        db.collection("Workspaces")
        .document(WORKSPACE_ID)
        .collection("Candidates")
        .document(CANDIDATE_REFERENCE_ID)
        .set(candidate_doc)
    )
    print(f"Seeded candidate: /Workspaces/{WORKSPACE_ID}/Candidates/{CANDIDATE_REFERENCE_ID}")

    # Seed AtsDocuments at /Workspaces/{WID}/Candidate/{CID}/AtsDocuments
    # Load sources.json for resume content if available
    sources_path = PROJECT_ROOT / "sources.json"
    resume_content = ""
    if sources_path.exists():
        raw = sources_path.read_text()
        sources_data = json.loads("{" + raw + "}")
        resume_content = "\n".join(
            s.get("source_content", "") for s in sources_data.get("sources", [])
        )

    vacancy_path = PROJECT_ROOT / "dentist.txt"
    job_desc = vacancy_path.read_text() if vacancy_path.exists() else ""

    ats_docs_ref = (
        db.collection("Workspaces")
        .document(WORKSPACE_ID)
        .collection("Candidate")
        .document(CANDIDATE_REFERENCE_ID)
        .collection("AtsDocuments")
    )
    if resume_content:
        ats_docs_ref.document("resume").set({"resume": resume_content})
    if job_desc:
        ats_docs_ref.document("jobDescription").set({"jobDescription": job_desc})
    print(
        f"Seeded AtsDocuments: /Workspaces/{WORKSPACE_ID}/Candidate/{CANDIDATE_REFERENCE_ID}/AtsDocuments"
    )

    # Seed vacancy at /Workspaces/{WID}/ATSVacancies/{VID}
    vacancy_description = vacancy_path.read_text() if vacancy_path.exists() else ""
    vacancy_doc = {
        "id": VACANCY_REFERENCE_ID,
        "title": "Tandartsassistent / Orthoassistent",
        "description": vacancy_description,
        "hard_requirements": "BIG registratie, MBO4 Tandartsassistent",
        "soft_requirements": "Teamplayer, communicatief sterk",
        "about_company": "Moderne tandartspraktijk in het Westland",
        "address": {"city": "Westland", "country": "Netherlands"},
        "status": "open",
        "workspace_id": WORKSPACE_ID,
    }
    (
        db.collection("Workspaces")
        .document(WORKSPACE_ID)
        .collection("ATSVacancies")
        .document(VACANCY_REFERENCE_ID)
        .set(vacancy_doc)
    )
    print(f"Seeded vacancy: /Workspaces/{WORKSPACE_ID}/ATSVacancies/{VACANCY_REFERENCE_ID}")

    print("Done.")


if __name__ == "__main__":
    main()

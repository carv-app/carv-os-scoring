"""Seed Firestore with sample candidate and vacancy data from local files."""

import json
import sys
from pathlib import Path

from google.cloud import firestore

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CANDIDATE_ID = "candidate-001"
VACANCY_ID = "vacancy-001"


def main():
    project_id = sys.argv[1] if len(sys.argv) > 1 else None
    if not project_id:
        print("Usage: python seed_firestore.py <gcp-project-id>")
        sys.exit(1)

    db = firestore.Client(project=project_id)

    # Load and parse sources.json
    sources_path = PROJECT_ROOT / "sources.json"
    raw = sources_path.read_text()
    # The file contains a JSON fragment with "sources": [...] — wrap it
    sources_data = json.loads("{" + raw + "}")

    candidate_doc = {
        "name": "Thomas Alexander van den Berg-Smit",
        "sources": sources_data["sources"],
    }
    db.collection("candidates").document(CANDIDATE_ID).set(candidate_doc)
    print(f"Seeded candidate: {CANDIDATE_ID}")

    # Load dentist.txt as vacancy description
    vacancy_path = PROJECT_ROOT / "dentist.txt"
    vacancy_description = vacancy_path.read_text()

    vacancy_doc = {
        "title": "Tandartsassistent / Orthoassistent",
        "description": vacancy_description,
    }
    db.collection("vacancies").document(VACANCY_ID).set(vacancy_doc)
    print(f"Seeded vacancy: {VACANCY_ID}")

    print("Done.")


if __name__ == "__main__":
    main()

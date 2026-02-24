resource "google_firestore_database" "default" {
  name        = "(default)"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"

  depends_on = [google_project_service.apis]
}

resource "google_firestore_index" "scoring_results_by_vacancy_score" {
  database   = google_firestore_database.default.name
  collection = "scoring_results"

  fields {
    field_path = "vacancy_id"
    order      = "ASCENDING"
  }
  fields {
    field_path = "score"
    order      = "DESCENDING"
  }
}

resource "google_firestore_index" "scoring_results_by_candidate_time" {
  database   = google_firestore_database.default.name
  collection = "scoring_results"

  fields {
    field_path = "candidate_id"
    order      = "ASCENDING"
  }
  fields {
    field_path = "scored_at"
    order      = "DESCENDING"
  }
}

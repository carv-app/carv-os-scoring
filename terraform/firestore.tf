resource "google_firestore_index" "scoring_results_by_vacancy_score" {
  database   = var.firestore_database_name
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
  database   = var.firestore_database_name
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

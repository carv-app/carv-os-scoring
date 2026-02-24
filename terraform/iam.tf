# Service account for the scoring Cloud Run service
resource "google_service_account" "scoring_service" {
  account_id   = "scoring-service"
  display_name = "Scoring Service"
  description  = "Service account for the candidate scoring Cloud Run service"
}

# Firestore read/write
resource "google_project_iam_member" "scoring_firestore" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.scoring_service.email}"
}

# Cloud Trace agent
resource "google_project_iam_member" "scoring_trace" {
  project = var.project_id
  role    = "roles/cloudtrace.agent"
  member  = "serviceAccount:${google_service_account.scoring_service.email}"
}

# Cloud Monitoring metric writer
resource "google_project_iam_member" "scoring_monitoring" {
  project = var.project_id
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${google_service_account.scoring_service.email}"
}

# Vertex AI user (for Gemini API)
resource "google_project_iam_member" "scoring_vertex_ai" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.scoring_service.email}"
}

# Pub/Sub publisher (for carv.score.* events)
resource "google_pubsub_topic_iam_member" "scoring_publish_calculated" {
  topic  = google_pubsub_topic.carv_score_calculated.id
  role   = "roles/pubsub.publisher"
  member = "serviceAccount:${google_service_account.scoring_service.email}"
}

resource "google_pubsub_topic_iam_member" "scoring_publish_failed" {
  topic  = google_pubsub_topic.carv_score_failed.id
  role   = "roles/pubsub.publisher"
  member = "serviceAccount:${google_service_account.scoring_service.email}"
}

# Service account for Pub/Sub push subscription OIDC auth
resource "google_service_account" "pubsub_invoker" {
  account_id   = "pubsub-invoker"
  display_name = "Pub/Sub Invoker"
  description  = "Service account for Pub/Sub push subscription to invoke Cloud Run"
}

# Allow Pub/Sub invoker to call Cloud Run
resource "google_cloud_run_v2_service_iam_member" "pubsub_invoker" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.scoring_worker.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.pubsub_invoker.email}"
}

output "cloud_run_url" {
  description = "URL of the Cloud Run scoring worker"
  value       = google_cloud_run_v2_service.scoring_worker.uri
}

output "input_topic" {
  description = "Pub/Sub topic the scoring worker subscribes to"
  value       = google_pubsub_topic.uats_application_created.name
}

output "score_calculated_topic" {
  description = "Pub/Sub topic for score calculated events"
  value       = google_pubsub_topic.carv_score_calculated.name
}

output "dlq_topic" {
  description = "Pub/Sub dead-letter topic"
  value       = google_pubsub_topic.scoring_dlq.name
}

output "service_account_email" {
  description = "Scoring service account email"
  value       = google_service_account.scoring_service.email
}

output "artifact_registry_repo" {
  description = "Artifact Registry repository URL"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.scoring.repository_id}"
}

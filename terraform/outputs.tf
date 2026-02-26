output "cloud_run_url" {
  description = "URL of the Cloud Run scoring worker"
  value       = google_cloud_run_v2_service.scoring_worker.uri
}

output "service_account_email" {
  description = "Scoring service account email"
  value       = google_service_account.scoring_service.email
}

output "artifact_registry_repo" {
  description = "Artifact Registry repository URL"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.scoring.repository_id}"
}

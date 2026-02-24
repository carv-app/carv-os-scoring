resource "google_artifact_registry_repository" "scoring" {
  location      = var.region
  repository_id = "scoring"
  format        = "DOCKER"
  description   = "Container images for the scoring service"

  depends_on = [google_project_service.apis]
}

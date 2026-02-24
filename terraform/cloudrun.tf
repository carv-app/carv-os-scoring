resource "google_cloud_run_v2_service" "scoring_worker" {
  name     = "scoring-worker"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_INTERNAL_ONLY"

  template {
    service_account = google_service_account.scoring_service.email

    scaling {
      min_instance_count = 1
      max_instance_count = 20
    }

    max_instance_request_concurrency = 10
    timeout                          = "300s"

    containers {
      image = var.scoring_image

      resources {
        limits = {
          cpu    = "2"
          memory = "1Gi"
        }
        cpu_idle = false # CPU always-on for OTel export between requests
      }

      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "GCP_REGION"
        value = var.region
      }
      env {
        name  = "OTEL_ENABLED"
        value = "true"
      }

      ports {
        container_port = 8080
      }

      startup_probe {
        http_get {
          path = "/health"
        }
        initial_delay_seconds = 5
        period_seconds        = 10
        failure_threshold     = 3
      }

      liveness_probe {
        http_get {
          path = "/health"
        }
        period_seconds = 30
      }
    }
  }

  depends_on = [google_project_service.apis]
}

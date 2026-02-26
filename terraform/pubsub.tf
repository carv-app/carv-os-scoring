# Dead-letter topic for failed scoring attempts
resource "google_pubsub_topic" "scoring_dlq" {
  name = "scoring-dlq"

  depends_on = [google_project_service.apis]
}

# Push subscription: uats.application.created → scoring worker
resource "google_pubsub_subscription" "scoring_push" {
  name  = "scoring-worker-push"
  topic = var.input_topic_id

  ack_deadline_seconds = 300

  push_config {
    push_endpoint = "${google_cloud_run_v2_service.scoring_worker.uri}/process-candidate"

    oidc_token {
      service_account_email = google_service_account.pubsub_invoker.email
    }
  }

  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.scoring_dlq.id
    max_delivery_attempts = 5
  }

  depends_on = [google_project_service.apis]
}

# Pub/Sub needs publisher role on DLQ topic to forward dead-lettered messages
data "google_project" "current" {}

resource "google_pubsub_topic_iam_member" "dlq_publisher" {
  topic  = google_pubsub_topic.scoring_dlq.id
  role   = "roles/pubsub.publisher"
  member = "serviceAccount:service-${data.google_project.current.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

# Pub/Sub needs subscriber role on main subscription to manage ack/nack
resource "google_pubsub_subscription_iam_member" "main_subscriber" {
  subscription = google_pubsub_subscription.scoring_push.id
  role         = "roles/pubsub.subscriber"
  member       = "serviceAccount:service-${data.google_project.current.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

# DLQ pull subscription for monitoring/draining dead-lettered messages
resource "google_pubsub_subscription" "scoring_dlq_pull" {
  name  = "scoring-dlq-pull"
  topic = google_pubsub_topic.scoring_dlq.id

  ack_deadline_seconds = 60

  depends_on = [google_project_service.apis]
}

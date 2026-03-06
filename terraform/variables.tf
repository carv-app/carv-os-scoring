variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "europe-west1"
}

variable "scoring_image" {
  description = "Container image for the scoring worker"
  type        = string
}

variable "gcs_bucket" {
  description = "GCS bucket for candidate documents (PDFs)"
  type        = string
  default     = "carv-dev-ats-candidate-documents"
}

variable "alert_notification_channel" {
  description = "Notification channel ID for monitoring alerts"
  type        = string
  default     = ""
}

variable "input_topic_id" {
  description = "Pub/Sub topic ID for incoming application events"
  type        = string
}

variable "score_calculated_topic_id" {
  description = "Pub/Sub topic ID for score calculated events"
  type        = string
}

variable "score_failed_topic_id" {
  description = "Pub/Sub topic ID for score failed events"
  type        = string
}

variable "scoring_dlq_topic_id" {
  description = "Pub/Sub topic ID for the scoring dead-letter queue"
  type        = string
}

variable "firestore_database_name" {
  description = "Firestore database name"
  type        = string
}

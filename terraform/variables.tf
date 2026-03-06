variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "europe-west1"
}

variable "zone" {
  description = "GCP zone"
  type        = string
  default     = ""
}

variable "cluster_name" {
  description = "GKE cluster name"
  type        = string
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
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

variable "incoming_topic_id" {
  description = "Pub/Sub topic ID for incoming events (subscription source)"
  type        = string
}

variable "outgoing_topic_id" {
  description = "Pub/Sub topic ID for publishing outgoing events"
  type        = string
}

variable "outgoing_topic_name" {
  description = "Pub/Sub topic short name for publishing outgoing events (e.g. carv-events-dev)"
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

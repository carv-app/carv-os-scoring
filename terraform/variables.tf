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

variable "firestore_database_name" {
  description = "Firestore database name"
  type        = string
}

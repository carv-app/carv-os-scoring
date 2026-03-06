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

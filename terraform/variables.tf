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

variable "alert_notification_channel" {
  description = "Notification channel ID for monitoring alerts"
  type        = string
  default     = ""
}

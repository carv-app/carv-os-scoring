resource "google_monitoring_alert_policy" "dlq_messages" {
  display_name = "Scoring DLQ - Undelivered Messages"
  combiner     = "OR"

  conditions {
    display_name = "DLQ has undelivered messages"

    condition_threshold {
      filter          = "resource.type = \"pubsub_subscription\" AND resource.labels.subscription_id = \"${google_pubsub_subscription.scoring_dlq_pull.name}\" AND metric.type = \"pubsub.googleapis.com/subscription/num_undelivered_messages\""
      comparison      = "COMPARISON_GT"
      threshold_value = 0
      duration        = "300s"

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MEAN"
      }
    }
  }

  dynamic "notification_channels" {
    for_each = var.alert_notification_channel != "" ? [var.alert_notification_channel] : []
    content {
    }
  }

  alert_strategy {
    auto_close = "1800s"
  }
}

resource "google_monitoring_alert_policy" "high_error_rate" {
  display_name = "Scoring Worker - High Error Rate"
  combiner     = "OR"

  conditions {
    display_name = "Error rate > 10%"

    condition_threshold {
      filter          = "resource.type = \"cloud_run_revision\" AND resource.labels.service_name = \"${google_cloud_run_v2_service.scoring_worker.name}\" AND metric.type = \"run.googleapis.com/request_count\" AND metric.labels.response_code_class = \"5xx\""
      comparison      = "COMPARISON_GT"
      threshold_value = 0.1
      duration        = "300s"

      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_RATE"
        cross_series_reducer = "REDUCE_SUM"
      }
    }
  }

  dynamic "notification_channels" {
    for_each = var.alert_notification_channel != "" ? [var.alert_notification_channel] : []
    content {
    }
  }

  alert_strategy {
    auto_close = "1800s"
  }
}

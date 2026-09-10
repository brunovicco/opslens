variable "scheduled_ingestion_enabled" {
  description = "Whether recurring EPSS, KEV, and NVD source-ingestion schedules may start new automatic invocations."
  type        = bool
  default     = true
}

locals {
  scheduled_ingestion_state = (
    var.scheduled_ingestion_enabled ? "ENABLED" : "DISABLED"
  )

  # Preserve the already-retained delivery-amplification boundary. These
  # values govern EventBridge Scheduler target retries only; downstream Lambda
  # asynchronous retry/failure-destination behavior remains independently
  # configured at each Lambda boundary.
  scheduled_ingestion_maximum_event_age_in_seconds = 3600
  scheduled_ingestion_maximum_retry_attempts       = 2
}

check "scheduled_ingestion_retry_budget" {
  assert {
    condition = (
      local.scheduled_ingestion_maximum_event_age_in_seconds == 3600 &&
      local.scheduled_ingestion_maximum_retry_attempts == 2
    )
    error_message = "Scheduled source ingestion must retain the 3600-second event-age and two-retry delivery budget."
  }
}

output "scheduled_ingestion_control" {
  description = "Terraform-owned operational state for recurring source-ingestion schedules."
  value = {
    enabled                   = var.scheduled_ingestion_enabled
    scheduler_state           = local.scheduled_ingestion_state
    maximum_event_age_seconds = local.scheduled_ingestion_maximum_event_age_in_seconds
    maximum_retry_attempts    = local.scheduled_ingestion_maximum_retry_attempts
  }
}

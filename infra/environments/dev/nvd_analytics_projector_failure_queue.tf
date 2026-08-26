resource "aws_sqs_queue" "nvd_analytics_projector_failures" {
  name = "opslens-dev-nvd-analytics-projector-failures"

  fifo_queue = false

  message_retention_seconds = 1209600

  sqs_managed_sse_enabled = true

  tags = {
    Purpose = "nvd-analytics-projector-failure-recovery"
  }
}

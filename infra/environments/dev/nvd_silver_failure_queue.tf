resource "aws_sqs_queue" "nvd_silver_failures" {
  name = "opslens-dev-nvd-silver-failures"

  fifo_queue = false

  message_retention_seconds = 1209600

  sqs_managed_sse_enabled = true

  tags = {
    Purpose = "nvd-silver-failure-recovery"
  }
}

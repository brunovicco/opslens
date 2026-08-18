resource "aws_sqs_queue" "kev_silver_failures" {
  name = "opslens-dev-kev-silver-failures"

  fifo_queue = false

  message_retention_seconds = 1209600

  sqs_managed_sse_enabled = true

  tags = {
    Purpose = "kev-silver-failure-recovery"
  }
}

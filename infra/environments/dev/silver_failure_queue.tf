resource "aws_sqs_queue" "epss_silver_failures" {
  name = "opslens-dev-epss-silver-failures"

  fifo_queue = false

  message_retention_seconds = 1209600

  sqs_managed_sse_enabled = true

  tags = {
    Purpose = "epss-silver-failure-recovery"
  }
}

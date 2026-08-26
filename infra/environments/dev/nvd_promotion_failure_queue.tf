resource "aws_sqs_queue" "nvd_promotion_failures" {
  name = "opslens-dev-nvd-promotion-failures"

  fifo_queue = false

  message_retention_seconds = 1209600

  sqs_managed_sse_enabled = true

  tags = {
    Purpose = "nvd-promotion-failure-recovery"
  }
}

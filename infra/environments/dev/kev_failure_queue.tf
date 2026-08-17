resource "aws_sqs_queue" "kev_ingestion_failures" {
  name = "opslens-dev-kev-ingestion-failures"

  fifo_queue = false

  message_retention_seconds = 1209600

  sqs_managed_sse_enabled = true

  tags = {
    Purpose = "kev-ingestion-failure-recovery"
  }
}

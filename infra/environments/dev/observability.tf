resource "aws_cloudwatch_log_group" "platform" {
  # checkov:skip=CKV_AWS_158: CloudWatch Logs encrypts data at rest by default; a customer-managed KMS key is not justified for the Phase 0 dev foundation.
  # checkov:skip=CKV_AWS_338: A 14-day retention period is intentional for the low-volume dev environment; one-year retention is not justified for this portfolio workload.

  name              = "/opslens/dev/platform"
  retention_in_days = 14
  log_group_class   = "STANDARD"

  tags = {
    Purpose = "platform-observability"
  }
}

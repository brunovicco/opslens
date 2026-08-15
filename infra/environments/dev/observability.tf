resource "aws_cloudwatch_log_group" "epss_ingestion" {
  # checkov:skip=CKV_AWS_158: CloudWatch Logs encryption at rest is sufficient for this dev workload; a customer-managed KMS key is not justified in Phase 1.
  # checkov:skip=CKV_AWS_338: A 14-day retention period is intentional for the low-volume dev environment.

  name              = local.epss_lambda_log_group_name
  retention_in_days = 14
  log_group_class   = "STANDARD"

  tags = {
    Purpose = "epss-ingestion-observability"
  }
}

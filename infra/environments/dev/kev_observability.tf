resource "aws_cloudwatch_log_group" "kev_ingestion" {
  # checkov:skip=CKV_AWS_158: CloudWatch Logs encryption at rest is sufficient for this dev workload; a customer-managed KMS key is not justified for the public CISA KEV dataset.
  # checkov:skip=CKV_AWS_338: A 14-day retention period is intentional for the low-volume dev environment.

  name              = local.kev_lambda_log_group_name
  retention_in_days = 14
  log_group_class   = "STANDARD"

  tags = {
    Purpose = "kev-ingestion-observability"
  }
}

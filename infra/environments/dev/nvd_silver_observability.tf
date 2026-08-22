resource "aws_cloudwatch_log_group" "nvd_silver" {
  # checkov:skip=CKV_AWS_158: CloudWatch Logs encryption at rest is sufficient for this dev workload containing public NVD data.
  # checkov:skip=CKV_AWS_338: A 14-day retention period is intentional for the low-volume dev environment.

  name              = local.nvd_silver_lambda_log_group_name
  retention_in_days = 14
  log_group_class   = "STANDARD"

  tags = {
    Purpose = "nvd-silver-observability"
  }
}

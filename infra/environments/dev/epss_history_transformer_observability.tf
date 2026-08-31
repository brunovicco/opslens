resource "aws_cloudwatch_log_group" "epss_history_transformer" {
  # checkov:skip=CKV_AWS_158: CloudWatch Logs encryption at rest is sufficient for this bounded dev bootstrap workload.
  # checkov:skip=CKV_AWS_338: A 14-day retention period is intentional for the bounded dev canary.

  name              = local.epss_history_transformer_log_group_name
  retention_in_days = 14
  log_group_class   = "STANDARD"

  tags = {
    Purpose = "epss-history-transformer-observability"
  }
}

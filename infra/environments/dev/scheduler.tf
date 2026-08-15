resource "aws_scheduler_schedule_group" "epss" {
  name = local.epss_scheduler_schedule_group_name

  tags = {
    Purpose = "epss-scheduling"
  }
}

resource "aws_scheduler_schedule" "epss_daily" {
  # checkov:skip=CKV_AWS_297:The Scheduler payload contains no sensitive data; AWS-owned encryption is sufficient for the current dev workload.
  name        = "opslens-dev-epss-daily"
  group_name  = aws_scheduler_schedule_group.epss.name
  description = "Daily ingestion of the FIRST EPSS snapshot into the OpsLens Bronze data lake."

  state = "ENABLED"

  schedule_expression          = "cron(0 14 * * ? *)"
  schedule_expression_timezone = "UTC"

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = aws_lambda_function.epss_ingestion.arn
    role_arn = aws_iam_role.epss_scheduler_execution.arn

    input = jsonencode({})

    retry_policy {
      maximum_event_age_in_seconds = 3600
      maximum_retry_attempts       = 2
    }
  }

  depends_on = [
    aws_iam_role_policy.epss_scheduler_runtime,
  ]
}

output "epss_scheduler_schedule_arn" {
  description = "ARN of the daily EPSS ingestion schedule."
  value       = aws_scheduler_schedule.epss_daily.arn
}

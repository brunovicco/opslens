resource "aws_scheduler_schedule_group" "kev" {
  name = local.kev_scheduler_schedule_group_name

  tags = {
    Purpose = "kev-scheduling"
  }
}

resource "aws_scheduler_schedule" "kev_daily" {
  # checkov:skip=CKV_AWS_297:The Scheduler payload contains no sensitive data; AWS-owned encryption is sufficient for the current dev workload.
  name        = "opslens-dev-kev-daily"
  group_name  = aws_scheduler_schedule_group.kev.name
  description = "Daily ingestion of the CISA KEV catalog into the OpsLens Bronze data lake."

  state = "ENABLED"

  schedule_expression          = "cron(30 23 * * ? *)"
  schedule_expression_timezone = "UTC"

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = aws_lambda_function.kev_ingestion.arn
    role_arn = aws_iam_role.kev_scheduler_execution.arn

    input = jsonencode({})

    retry_policy {
      maximum_event_age_in_seconds = 3600
      maximum_retry_attempts       = 2
    }
  }

  depends_on = [
    aws_iam_role_policy.kev_scheduler_runtime,
  ]
}

output "kev_scheduler_schedule_arn" {
  description = "ARN of the daily KEV ingestion schedule."
  value       = aws_scheduler_schedule.kev_daily.arn
}

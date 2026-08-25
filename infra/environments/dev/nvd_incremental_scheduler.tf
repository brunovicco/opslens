locals {
  nvd_incremental_scheduler_group_name = "opslens-dev-nvd-incremental"
  nvd_incremental_scheduler_name       = "opslens-dev-nvd-incremental-hourly"
}

resource "aws_scheduler_schedule_group" "nvd_incremental" {
  name = local.nvd_incremental_scheduler_group_name

  tags = {
    Project     = "opslens"
    Environment = "dev"
    ManagedBy   = "terraform"
    Repository  = "brunovicco/opslens"
    Purpose     = "nvd-incremental-scheduling"
  }
}

data "aws_iam_policy_document" "nvd_incremental_scheduler_assume_role" {
  statement {
    sid     = "AllowEventBridgeSchedulerAssumeRole"
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["scheduler.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }

    condition {
      test     = "ArnEquals"
      variable = "aws:SourceArn"
      values   = [aws_scheduler_schedule_group.nvd_incremental.arn]
    }
  }
}

resource "aws_iam_role" "nvd_incremental_scheduler_execution" {
  name = "OpsLensNvdIncrementalSchedulerExecutionRole"

  assume_role_policy = data.aws_iam_policy_document.nvd_incremental_scheduler_assume_role.json

  tags = {
    Project     = "opslens"
    Environment = "dev"
    ManagedBy   = "terraform"
    Repository  = "brunovicco/opslens"
    Purpose     = "nvd-incremental-scheduling"
  }
}

data "aws_iam_policy_document" "nvd_incremental_scheduler_runtime" {
  statement {
    sid    = "InvokeNvdIncrementalLambda"
    effect = "Allow"

    actions = [
      "lambda:InvokeFunction",
    ]

    resources = [
      aws_lambda_function.nvd_incremental.arn,
    ]
  }
}

resource "aws_iam_role_policy" "nvd_incremental_scheduler_runtime" {
  name = "OpsLensNvdIncrementalSchedulerRuntimeAccess"
  role = aws_iam_role.nvd_incremental_scheduler_execution.id

  policy = data.aws_iam_policy_document.nvd_incremental_scheduler_runtime.json
}

resource "aws_scheduler_schedule" "nvd_incremental_hourly" {
  name       = local.nvd_incremental_scheduler_name
  group_name = aws_scheduler_schedule_group.nvd_incremental.name

  description = "Invoke the OpsLens NVD incremental ingestion runtime hourly."

  state = "DISABLED"

  schedule_expression          = "cron(25 * * * ? *)"
  schedule_expression_timezone = "UTC"

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = aws_lambda_function.nvd_incremental.arn
    role_arn = aws_iam_role.nvd_incremental_scheduler_execution.arn

    input = jsonencode({
      schema_version = "1"
      target_end_at  = "<aws.scheduler.scheduled-time>"
    })

    retry_policy {
      maximum_event_age_in_seconds = 3600
      maximum_retry_attempts       = 2
    }
  }

  depends_on = [
    aws_iam_role_policy.nvd_incremental_scheduler_runtime,
  ]
}

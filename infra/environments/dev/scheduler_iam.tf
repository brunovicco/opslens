locals {
  epss_scheduler_schedule_group_name = "opslens-dev-epss"

  epss_scheduler_schedule_group_arn = (
    "arn:aws:scheduler:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:schedule-group/${local.epss_scheduler_schedule_group_name}"
  )

  epss_scheduler_execution_role_name = "OpsLensEpssSchedulerExecutionRole"
}

data "aws_iam_policy_document" "epss_scheduler_assume_role" {
  statement {
    sid     = "AllowEventBridgeScheduler"
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
      test     = "StringEquals"
      variable = "aws:SourceArn"
      values   = [local.epss_scheduler_schedule_group_arn]
    }
  }
}

resource "aws_iam_role" "epss_scheduler_execution" {
  name        = local.epss_scheduler_execution_role_name
  description = "Execution role used by EventBridge Scheduler to invoke the OpsLens EPSS ingestion Lambda."

  assume_role_policy = data.aws_iam_policy_document.epss_scheduler_assume_role.json

  tags = {
    Purpose = "epss-scheduler-runtime"
  }
}

data "aws_iam_policy_document" "epss_scheduler_runtime" {
  statement {
    sid    = "InvokeEpssIngestionLambda"
    effect = "Allow"

    actions = [
      "lambda:InvokeFunction",
    ]

    resources = [
      aws_lambda_function.epss_ingestion.arn,
    ]
  }
}

resource "aws_iam_role_policy" "epss_scheduler_runtime" {
  name = "OpsLensEpssSchedulerRuntimeAccess"
  role = aws_iam_role.epss_scheduler_execution.id

  policy = data.aws_iam_policy_document.epss_scheduler_runtime.json
}

output "epss_scheduler_execution_role_arn" {
  description = "ARN of the EPSS EventBridge Scheduler execution role."
  value       = aws_iam_role.epss_scheduler_execution.arn
}

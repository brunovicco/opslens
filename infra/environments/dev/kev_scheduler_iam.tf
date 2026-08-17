locals {
  kev_scheduler_schedule_group_name = "opslens-dev-kev"

  kev_scheduler_schedule_group_arn = (
    "arn:aws:scheduler:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:schedule-group/${local.kev_scheduler_schedule_group_name}"
  )

  kev_scheduler_execution_role_name = "OpsLensKevSchedulerExecutionRole"
}

data "aws_iam_policy_document" "kev_scheduler_assume_role" {
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
      values   = [local.kev_scheduler_schedule_group_arn]
    }
  }
}

resource "aws_iam_role" "kev_scheduler_execution" {
  name        = local.kev_scheduler_execution_role_name
  description = "Execution role used by EventBridge Scheduler to invoke the OpsLens KEV ingestion Lambda."

  assume_role_policy = data.aws_iam_policy_document.kev_scheduler_assume_role.json

  tags = {
    Purpose = "kev-scheduler-runtime"
  }
}

data "aws_iam_policy_document" "kev_scheduler_runtime" {
  statement {
    sid    = "InvokeKevIngestionLambda"
    effect = "Allow"

    actions = [
      "lambda:InvokeFunction",
    ]

    resources = [
      aws_lambda_function.kev_ingestion.arn,
    ]
  }
}

resource "aws_iam_role_policy" "kev_scheduler_runtime" {
  name = "OpsLensKevSchedulerRuntimeAccess"
  role = aws_iam_role.kev_scheduler_execution.id

  policy = data.aws_iam_policy_document.kev_scheduler_runtime.json
}

output "kev_scheduler_execution_role_arn" {
  description = "ARN of the KEV EventBridge Scheduler execution role."
  value       = aws_iam_role.kev_scheduler_execution.arn
}

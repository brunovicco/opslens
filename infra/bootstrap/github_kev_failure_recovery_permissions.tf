locals {
  dev_kev_ingestion_failures_queue_name = "opslens-dev-kev-ingestion-failures"

  dev_kev_ingestion_failures_queue_arn = (
    "arn:aws:sqs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:${local.dev_kev_ingestion_failures_queue_name}"
  )
}

data "aws_iam_policy_document" "github_actions_kev_failure_recovery" {
  statement {
    sid    = "ManageKevIngestionFailureQueue"
    effect = "Allow"

    actions = [
      "sqs:CreateQueue",
      "sqs:DeleteQueue",
      "sqs:GetQueueAttributes",
      "sqs:GetQueueUrl",
      "sqs:ListQueueTags",
      "sqs:SetQueueAttributes",
      "sqs:TagQueue",
      "sqs:UntagQueue",
    ]

    resources = [
      local.dev_kev_ingestion_failures_queue_arn,
    ]
  }

  statement {
    sid    = "ManageKevLambdaEventInvokeConfig"
    effect = "Allow"

    actions = [
      "lambda:DeleteFunctionEventInvokeConfig",
      "lambda:GetFunctionEventInvokeConfig",
      "lambda:PutFunctionEventInvokeConfig",
      "lambda:UpdateFunctionEventInvokeConfig",
    ]

    resources = [
      local.dev_kev_lambda_function_arn,
    ]
  }
}

resource "aws_iam_policy" "github_actions_kev_failure_recovery" {
  name = "OpsLensKevFailureRecoveryDev"

  description = "Allow OpsLens GitHub deployment automation to manage KEV asynchronous failure recovery."

  policy = data.aws_iam_policy_document.github_actions_kev_failure_recovery.json
}

resource "aws_iam_role_policy_attachment" "github_actions_kev_failure_recovery" {
  role = aws_iam_role.github_actions_deploy.name

  policy_arn = aws_iam_policy.github_actions_kev_failure_recovery.arn
}

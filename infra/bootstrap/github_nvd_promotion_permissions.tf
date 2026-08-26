locals {
  github_nvd_promotion_lambda_function_name = "opslens-dev-nvd-promotion"

  github_nvd_promotion_lambda_function_arn = (
    "arn:aws:lambda:${var.aws_region}:${data.aws_caller_identity.current.account_id}:function:${local.github_nvd_promotion_lambda_function_name}"
  )

  github_nvd_promotion_execution_role_name = "OpsLensNvdPromotionLambdaRole"

  github_nvd_promotion_execution_role_arn = (
    "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${local.github_nvd_promotion_execution_role_name}"
  )

  github_nvd_promotion_failures_queue_name = "opslens-dev-nvd-promotion-failures"

  github_nvd_promotion_failures_queue_arn = (
    "arn:aws:sqs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:${local.github_nvd_promotion_failures_queue_name}"
  )

  github_nvd_promotion_log_group_name = (
    "/aws/lambda/${local.github_nvd_promotion_lambda_function_name}"
  )

  github_nvd_promotion_log_group_arn = (
    "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:${local.github_nvd_promotion_log_group_name}"
  )
}

data "aws_iam_policy_document" "github_nvd_promotion_deploy" {
  statement {
    sid    = "ManageNvdPromotionExecutionRole"
    effect = "Allow"

    actions = [
      "iam:CreateRole",
      "iam:DeleteRole",
      "iam:GetRole",
      "iam:GetRolePolicy",
      "iam:ListAttachedRolePolicies",
      "iam:ListInstanceProfilesForRole",
      "iam:ListRolePolicies",
      "iam:ListRoleTags",
      "iam:TagRole",
      "iam:UntagRole",
      "iam:UpdateAssumeRolePolicy",
      "iam:PutRolePolicy",
      "iam:DeleteRolePolicy",
    ]

    resources = [
      local.github_nvd_promotion_execution_role_arn,
    ]
  }

  statement {
    sid    = "PassNvdPromotionExecutionRoleToLambda"
    effect = "Allow"

    actions = [
      "iam:PassRole",
    ]

    resources = [
      local.github_nvd_promotion_execution_role_arn,
    ]

    condition {
      test     = "StringEquals"
      variable = "iam:PassedToService"

      values = [
        "lambda.amazonaws.com",
      ]
    }
  }

  statement {
    sid    = "ManageNvdPromotionLambda"
    effect = "Allow"

    actions = [
      "lambda:CreateFunction",
      "lambda:DeleteFunction",
      "lambda:GetFunction",
      "lambda:GetFunctionCodeSigningConfig",
      "lambda:GetFunctionConcurrency",
      "lambda:GetFunctionConfiguration",
      "lambda:GetFunctionEventInvokeConfig",
      "lambda:GetFunctionRecursionConfig",
      "lambda:GetRuntimeManagementConfig",
      "lambda:ListTags",
      "lambda:ListVersionsByFunction",
      "lambda:PutFunctionEventInvokeConfig",
      "lambda:TagResource",
      "lambda:UntagResource",
      "lambda:UpdateFunctionCode",
      "lambda:UpdateFunctionConfiguration",
      "lambda:UpdateFunctionEventInvokeConfig",
      "lambda:DeleteFunctionEventInvokeConfig",
    ]

    resources = [
      local.github_nvd_promotion_lambda_function_arn,
    ]
  }

  statement {
    sid    = "AllowS3InvokePermissionOnNvdPromotion"
    effect = "Allow"

    actions = [
      "lambda:AddPermission",
    ]

    resources = [
      local.github_nvd_promotion_lambda_function_arn,
    ]

    condition {
      test     = "StringEquals"
      variable = "lambda:Principal"

      values = [
        "s3.amazonaws.com",
      ]
    }
  }

  statement {
    sid    = "ReadAndRemoveNvdPromotionLambdaPolicy"
    effect = "Allow"

    actions = [
      "lambda:GetPolicy",
      "lambda:RemovePermission",
    ]

    resources = [
      local.github_nvd_promotion_lambda_function_arn,
    ]
  }

  statement {
    sid    = "ManageNvdPromotionFailureQueue"
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
      local.github_nvd_promotion_failures_queue_arn,
    ]
  }

  statement {
    sid    = "ManageNvdPromotionLogGroupConfiguration"
    effect = "Allow"

    actions = [
      "logs:DeleteRetentionPolicy",
      "logs:ListTagsForResource",
      "logs:PutRetentionPolicy",
      "logs:TagResource",
      "logs:UntagResource",
    ]

    resources = [
      local.github_nvd_promotion_log_group_arn,
    ]
  }
}

resource "aws_iam_policy" "github_nvd_promotion_deploy" {
  name = "OpsLensGitHubNvdPromotionDeploy"

  description = (
    "Allow OpsLens GitHub deployment automation to reconcile the NVD promotion runtime."
  )

  policy = data.aws_iam_policy_document.github_nvd_promotion_deploy.json

  tags = {
    Purpose = "github-actions-nvd-promotion-deployment"
  }
}

resource "aws_iam_role_policy_attachment" "github_nvd_promotion_deploy" {
  role       = aws_iam_role.github_actions_deploy.name
  policy_arn = aws_iam_policy.github_nvd_promotion_deploy.arn
}

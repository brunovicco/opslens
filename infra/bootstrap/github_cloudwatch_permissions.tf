locals {
  dev_platform_log_group_name = "/opslens/dev/platform"

  # CloudWatch Logs uses two ARN forms:
  # - with :* for most log-group management actions;
  # - without :* for TagResource, UntagResource, and ListTagsForResource.
  dev_platform_log_group_arn     = "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:${local.dev_platform_log_group_name}"
  dev_platform_log_group_iam_arn = "${local.dev_platform_log_group_arn}:*"
}

data "aws_iam_policy_document" "github_actions_cloudwatch_logs" {
  statement {
    sid     = "DescribeDevLogGroups"
    effect  = "Allow"
    actions = ["logs:DescribeLogGroups"]

    resources = ["*"]
  }

  statement {
    sid    = "ManageDevPlatformLogGroup"
    effect = "Allow"

    actions = [
      "logs:CreateLogGroup",
      "logs:DeleteLogGroup",
      "logs:PutRetentionPolicy",
      "logs:DeleteRetentionPolicy",
    ]

    resources = [
      local.dev_platform_log_group_iam_arn,
    ]
  }

  statement {
    sid    = "TagDevPlatformLogGroup"
    effect = "Allow"

    actions = [
      "logs:TagResource",
      "logs:UntagResource",
      "logs:ListTagsForResource",
    ]

    resources = [
      local.dev_platform_log_group_arn,
    ]
  }
}

resource "aws_iam_role_policy" "github_actions_cloudwatch_logs" {
  name = "OpsLensCloudWatchLogsDevAccess"
  role = aws_iam_role.github_actions_deploy.id

  policy = data.aws_iam_policy_document.github_actions_cloudwatch_logs.json
}

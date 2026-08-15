locals {
  dev_epss_scheduler_execution_role_name = "OpsLensEpssSchedulerExecutionRole"

  dev_epss_scheduler_execution_role_arn = (
    "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${local.dev_epss_scheduler_execution_role_name}"
  )
}

data "aws_iam_policy_document" "github_actions_epss_scheduler_runtime_iam" {
  statement {
    sid    = "ManageEpssSchedulerExecutionRole"
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
      local.dev_epss_scheduler_execution_role_arn,
    ]
  }
}

resource "aws_iam_role_policy" "github_actions_epss_scheduler_runtime_iam" {
  name = "OpsLensEpssSchedulerRuntimeIamDevAccess"
  role = aws_iam_role.github_actions_deploy.id

  policy = data.aws_iam_policy_document.github_actions_epss_scheduler_runtime_iam.json
}

locals {
  dev_kev_scheduler_schedule_group_name = "opslens-dev-kev"
  dev_kev_scheduler_schedule_name       = "opslens-dev-kev-daily"

  dev_kev_scheduler_schedule_group_arn = (
    "arn:aws:scheduler:${var.aws_region}:${data.aws_caller_identity.current.account_id}:schedule-group/${local.dev_kev_scheduler_schedule_group_name}"
  )

  dev_kev_scheduler_schedule_arn = (
    "arn:aws:scheduler:${var.aws_region}:${data.aws_caller_identity.current.account_id}:schedule/${local.dev_kev_scheduler_schedule_group_name}/${local.dev_kev_scheduler_schedule_name}"
  )

  dev_kev_scheduler_execution_role_name = "OpsLensKevSchedulerExecutionRole"

  dev_kev_scheduler_execution_role_arn = (
    "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${local.dev_kev_scheduler_execution_role_name}"
  )
}

data "aws_iam_policy_document" "github_actions_kev_scheduler" {
  statement {
    sid    = "CreateKevScheduleGroup"
    effect = "Allow"

    actions = [
      "scheduler:CreateScheduleGroup",
    ]

    resources = [
      local.dev_kev_scheduler_schedule_group_arn,
    ]

    condition {
      test     = "StringEquals"
      variable = "aws:RequestTag/Project"
      values   = ["opslens"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:RequestTag/Environment"
      values   = ["dev"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:RequestTag/ManagedBy"
      values   = ["terraform"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:RequestTag/Repository"
      values   = ["brunovicco/opslens"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:RequestTag/Purpose"
      values   = ["kev-scheduling"]
    }

    condition {
      test     = "ForAllValues:StringEquals"
      variable = "aws:TagKeys"

      values = [
        "Project",
        "Environment",
        "ManagedBy",
        "Repository",
        "Purpose",
      ]
    }
  }

  statement {
    sid    = "ManageKevScheduleGroup"
    effect = "Allow"

    actions = [
      "scheduler:DeleteScheduleGroup",
      "scheduler:GetScheduleGroup",
      "scheduler:ListTagsForResource",
      "scheduler:TagResource",
      "scheduler:UntagResource",
    ]

    resources = [
      local.dev_kev_scheduler_schedule_group_arn,
    ]
  }

  statement {
    sid    = "ManageKevSchedule"
    effect = "Allow"

    actions = [
      "scheduler:CreateSchedule",
      "scheduler:DeleteSchedule",
      "scheduler:GetSchedule",
      "scheduler:UpdateSchedule",
    ]

    resources = [
      local.dev_kev_scheduler_schedule_arn,
    ]
  }

  statement {
    sid    = "ManageKevSchedulerExecutionRole"
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
      local.dev_kev_scheduler_execution_role_arn,
    ]
  }

  statement {
    sid    = "PassKevSchedulerExecutionRole"
    effect = "Allow"

    actions = [
      "iam:PassRole",
    ]

    resources = [
      local.dev_kev_scheduler_execution_role_arn,
    ]

    condition {
      test     = "StringEquals"
      variable = "iam:PassedToService"
      values   = ["scheduler.amazonaws.com"]
    }
  }
}

resource "aws_iam_policy" "github_actions_kev_scheduler" {
  name = "OpsLensKevSchedulerDev"

  description = "Allow OpsLens GitHub deployment automation to manage the KEV EventBridge Scheduler resources."

  policy = data.aws_iam_policy_document.github_actions_kev_scheduler.json
}

resource "aws_iam_role_policy_attachment" "github_actions_kev_scheduler" {
  role = aws_iam_role.github_actions_deploy.name

  policy_arn = aws_iam_policy.github_actions_kev_scheduler.arn
}

locals {
  dev_epss_scheduler_schedule_group_name = "opslens-dev-epss"
  dev_epss_scheduler_schedule_name       = "opslens-dev-epss-daily"

  dev_epss_scheduler_schedule_group_arn = (
    "arn:aws:scheduler:${var.aws_region}:${data.aws_caller_identity.current.account_id}:schedule-group/${local.dev_epss_scheduler_schedule_group_name}"
  )

  dev_epss_scheduler_schedule_arn = (
    "arn:aws:scheduler:${var.aws_region}:${data.aws_caller_identity.current.account_id}:schedule/${local.dev_epss_scheduler_schedule_group_name}/${local.dev_epss_scheduler_schedule_name}"
  )
}

data "aws_iam_policy_document" "github_actions_epss_scheduler" {
  statement {
    sid    = "CreateEpssScheduleGroup"
    effect = "Allow"

    actions = [
      "scheduler:CreateScheduleGroup",
    ]

    resources = [
      local.dev_epss_scheduler_schedule_group_arn,
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
      values   = ["epss-scheduling"]
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
    sid    = "ManageEpssScheduleGroup"
    effect = "Allow"

    actions = [
      "scheduler:DeleteScheduleGroup",
      "scheduler:GetScheduleGroup",
      "scheduler:ListTagsForResource",
      "scheduler:TagResource",
      "scheduler:UntagResource",
    ]

    resources = [
      local.dev_epss_scheduler_schedule_group_arn,
    ]
  }

  statement {
    sid    = "ManageEpssSchedule"
    effect = "Allow"

    actions = [
      "scheduler:CreateSchedule",
      "scheduler:DeleteSchedule",
      "scheduler:GetSchedule",
      "scheduler:UpdateSchedule",
    ]

    resources = [
      local.dev_epss_scheduler_schedule_arn,
    ]
  }

  statement {
    sid    = "PassEpssSchedulerExecutionRole"
    effect = "Allow"

    actions = [
      "iam:PassRole",
    ]

    resources = [
      local.dev_epss_scheduler_execution_role_arn,
    ]

    condition {
      test     = "StringEquals"
      variable = "iam:PassedToService"
      values   = ["scheduler.amazonaws.com"]
    }
  }
}

resource "aws_iam_role_policy" "github_actions_epss_scheduler" {
  name = "OpsLensEpssSchedulerDevAccess"
  role = aws_iam_role.github_actions_deploy.id

  policy = data.aws_iam_policy_document.github_actions_epss_scheduler.json
}

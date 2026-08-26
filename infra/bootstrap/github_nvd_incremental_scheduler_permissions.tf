locals {
  dev_nvd_incremental_scheduler_schedule_group_name = "opslens-dev-nvd-incremental"
  dev_nvd_incremental_scheduler_schedule_name       = "opslens-dev-nvd-incremental-hourly"
  dev_nvd_incremental_scheduler_execution_role_name = "OpsLensNvdIncrementalSchedulerExecutionRole"

  dev_nvd_incremental_scheduler_schedule_group_arn = format(
    "arn:aws:scheduler:%s:%s:schedule-group/%s",
    var.aws_region,
    data.aws_caller_identity.current.account_id,
    local.dev_nvd_incremental_scheduler_schedule_group_name,
  )

  dev_nvd_incremental_scheduler_schedule_arn = format(
    "arn:aws:scheduler:%s:%s:schedule/%s/%s",
    var.aws_region,
    data.aws_caller_identity.current.account_id,
    local.dev_nvd_incremental_scheduler_schedule_group_name,
    local.dev_nvd_incremental_scheduler_schedule_name,
  )

  dev_nvd_incremental_scheduler_execution_role_arn = format(
    "arn:aws:iam::%s:role/%s",
    data.aws_caller_identity.current.account_id,
    local.dev_nvd_incremental_scheduler_execution_role_name,
  )
}

data "aws_iam_policy_document" "github_actions_nvd_incremental_scheduler" {
  statement {
    sid    = "CreateNvdIncrementalScheduleGroup"
    effect = "Allow"

    actions = [
      "scheduler:CreateScheduleGroup",
    ]

    resources = [
      local.dev_nvd_incremental_scheduler_schedule_group_arn,
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
      values   = ["nvd-incremental-scheduling"]
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
    sid    = "ManageNvdIncrementalScheduleGroup"
    effect = "Allow"

    actions = [
      "scheduler:DeleteScheduleGroup",
      "scheduler:GetScheduleGroup",
      "scheduler:ListTagsForResource",
      "scheduler:TagResource",
      "scheduler:UntagResource",
    ]

    resources = [
      local.dev_nvd_incremental_scheduler_schedule_group_arn,
    ]
  }

  statement {
    sid    = "ManageNvdIncrementalSchedule"
    effect = "Allow"

    actions = [
      "scheduler:CreateSchedule",
      "scheduler:DeleteSchedule",
      "scheduler:GetSchedule",
      "scheduler:UpdateSchedule",
    ]

    resources = [
      local.dev_nvd_incremental_scheduler_schedule_arn,
    ]
  }

  statement {
    sid    = "ManageNvdIncrementalSchedulerExecutionRole"
    effect = "Allow"

    actions = [
      "iam:CreateRole",
      "iam:DeleteRole",
      "iam:DeleteRolePolicy",
      "iam:GetRole",
      "iam:GetRolePolicy",
      "iam:ListAttachedRolePolicies",
      "iam:ListInstanceProfilesForRole",
      "iam:ListRolePolicies",
      "iam:ListRoleTags",
      "iam:PutRolePolicy",
      "iam:TagRole",
      "iam:UntagRole",
      "iam:UpdateAssumeRolePolicy",
    ]

    resources = [
      local.dev_nvd_incremental_scheduler_execution_role_arn,
    ]
  }

  statement {
    sid    = "PassNvdIncrementalSchedulerExecutionRole"
    effect = "Allow"

    actions = [
      "iam:PassRole",
    ]

    resources = [
      local.dev_nvd_incremental_scheduler_execution_role_arn,
    ]

    condition {
      test     = "StringEquals"
      variable = "iam:PassedToService"
      values   = ["scheduler.amazonaws.com"]
    }
  }
}

resource "aws_iam_policy" "github_actions_nvd_incremental_scheduler" {
  name        = "OpsLensNvdIncrementalSchedulerDev"
  description = "Allow OpsLens GitHub deployment automation to manage the NVD incremental EventBridge Scheduler resources."

  policy = data.aws_iam_policy_document.github_actions_nvd_incremental_scheduler.json
}

resource "aws_iam_role_policy_attachment" "github_actions_nvd_incremental_scheduler" {
  role       = aws_iam_role.github_actions_deploy.id
  policy_arn = aws_iam_policy.github_actions_nvd_incremental_scheduler.arn
}

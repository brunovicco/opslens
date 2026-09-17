# Gate 21.2 — the cost ceiling that makes "public" a promise rather than a bill.
#
# Throttling bounds the rate. Reserved concurrency bounds how much runs at once. Neither
# bounds the month: a caller within every per-request limit, sustained, still spends. So
# the ceiling is a budget with an action attached, and the action removes the ability to
# invoke rather than sending a warning nobody is awake to read.
#
#   a rate limit != a spend limit
#   an alert != a control
#
# The action applies a deny policy to the API role. It does not delete the stage, empty a
# bucket or touch any evidence: the endpoint stops answering and everything that proves
# what it answered stays exactly where it is.
#
#   disabled != destroyed
#
# Nothing here is create-only by accident. The budget and its action are created by this
# file, and re-enabling after a trip is a human action taken deliberately, because an
# automatic reset would turn a ceiling into a speed bump.

variable "public_analysis_cost_ceiling_materialized" {
  description = "Create the Gate 21.2 monthly cost ceiling and its kill switch."
  type        = bool
  default     = false
}

variable "public_analysis_monthly_ceiling_usd" {
  description = "Hard monthly ceiling, in USD, at which public analysis is disabled."
  type        = number
  default     = 25

  validation {
    condition     = var.public_analysis_monthly_ceiling_usd > 0
    error_message = "A ceiling of zero disables the endpoint permanently rather than bounding it."
  }
}

variable "public_analysis_cost_ceiling_notification_email" {
  description = "Address notified before and when the ceiling trips. Empty disables notification."
  type        = string
  default     = ""
}

locals {
  public_analysis_cost_ceiling_count = (
    var.public_analysis_cost_ceiling_materialized ? 1 : 0
  )

  public_analysis_budget_name = "opslens-dev-public-analysis-monthly"

  # The alert fires first, the switch trips second. A ceiling with no warning is a
  # surprise; a warning with no ceiling is the thing this gate exists to replace.
  public_analysis_warning_threshold_percent = 60

  public_analysis_kill_switch_policy_name = "OpsLensPublicAnalysisCostCeilingDeny"
  public_analysis_kill_switch_role_name   = "OpsLensPublicAnalysisBudgetActionRole"

  public_analysis_cost_ceiling_subscribers = (
    var.public_analysis_cost_ceiling_notification_email == "" ? [] : [
      var.public_analysis_cost_ceiling_notification_email
    ]
  )
}

# What the action attaches. Deny is explicit rather than a permission removal, so it
# overrides anything the role is granted elsewhere, now or later.
resource "aws_iam_policy" "public_analysis_cost_ceiling_deny" {
  count = local.public_analysis_cost_ceiling_count

  name        = local.public_analysis_kill_switch_policy_name
  description = "Gate 21.2 kill switch: deny public-analysis invocation past the monthly ceiling."

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "DenyPublicAnalysisInvocation"
        Effect = "Deny"
        Action = [
          "lambda:InvokeFunction",
          "lambda:InvokeFunctionUrl",
        ]
        Resource = "*"
      },
    ]
  })

  tags = {
    Purpose = "public-analysis-cost-ceiling"
    Gate    = "21.2"
  }
}

data "aws_iam_policy_document" "public_analysis_budget_action_trust" {
  count = local.public_analysis_cost_ceiling_count

  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["budgets.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }
  }
}

data "aws_iam_policy_document" "public_analysis_budget_action" {
  count = local.public_analysis_cost_ceiling_count

  # Exactly the two calls the action makes, against exactly the policy it attaches.
  # Budgets is given the ability to trip this switch and nothing else.
  statement {
    effect = "Allow"
    actions = [
      "iam:AttachRolePolicy",
      "iam:DetachRolePolicy",
    ]
    resources = [
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${local.public_async_api_role_name}",
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${local.public_async_worker_role_name}",
    ]

    condition {
      test     = "ArnEquals"
      variable = "iam:PolicyARN"
      values   = [aws_iam_policy.public_analysis_cost_ceiling_deny[0].arn]
    }
  }
}

resource "aws_iam_role" "public_analysis_budget_action" {
  count = local.public_analysis_cost_ceiling_count

  name               = local.public_analysis_kill_switch_role_name
  description        = "Role AWS Budgets assumes to trip the Gate 21.2 kill switch."
  assume_role_policy = data.aws_iam_policy_document.public_analysis_budget_action_trust[0].json

  tags = {
    Purpose = "public-analysis-cost-ceiling"
    Gate    = "21.2"
  }
}

resource "aws_iam_role_policy" "public_analysis_budget_action" {
  count = local.public_analysis_cost_ceiling_count

  name   = "OpsLensPublicAnalysisBudgetActionInline"
  role   = aws_iam_role.public_analysis_budget_action[0].id
  policy = data.aws_iam_policy_document.public_analysis_budget_action[0].json
}

resource "aws_budgets_budget" "public_analysis_monthly" {
  count = local.public_analysis_cost_ceiling_count

  name         = local.public_analysis_budget_name
  budget_type  = "COST"
  limit_amount = tostring(var.public_analysis_monthly_ceiling_usd)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  # The warning. It carries no action: its whole job is to be read before the ceiling
  # trips, so a real spend pattern is noticed while it is still a question rather than an
  # outage.
  dynamic "notification" {
    for_each = local.public_analysis_cost_ceiling_subscribers

    content {
      comparison_operator        = "GREATER_THAN"
      threshold                  = local.public_analysis_warning_threshold_percent
      threshold_type             = "PERCENTAGE"
      notification_type          = "ACTUAL"
      subscriber_email_addresses = [notification.value]
    }
  }

  tags = {
    Purpose = "public-analysis-cost-ceiling"
    Gate    = "21.2"
  }
}

resource "aws_budgets_budget_action" "public_analysis_kill_switch" {
  count = local.public_analysis_cost_ceiling_count

  budget_name        = aws_budgets_budget.public_analysis_monthly[0].name
  action_type        = "APPLY_IAM_POLICY"
  approval_model     = "AUTOMATIC"
  notification_type  = "ACTUAL"
  execution_role_arn = aws_iam_role.public_analysis_budget_action[0].arn

  action_threshold {
    action_threshold_type  = "PERCENTAGE"
    action_threshold_value = 100
  }

  definition {
    iam_action_definition {
      policy_arn = aws_iam_policy.public_analysis_cost_ceiling_deny[0].arn
      roles = [
        local.public_async_api_role_name,
        local.public_async_worker_role_name,
      ]
    }
  }

  lifecycle {
    # The action attaches a policy to two roles by name. Those roles exist only when the
    # async runtime is materialized, and a switch wired to a role that does not exist is
    # a switch that fails at the moment it is needed.
    precondition {
      condition     = var.public_async_runtime_materialized
      error_message = "The cost ceiling attaches to the public-analysis roles, so the async runtime must be materialized first."
    }
  }

  # AUTOMATIC, deliberately. An approval model that waits for a human turns the ceiling
  # into a notification, and a notification is what this gate exists to replace.
  dynamic "subscriber" {
    for_each = local.public_analysis_cost_ceiling_subscribers

    content {
      address           = subscriber.value
      subscription_type = "EMAIL"
    }
  }
}

output "public_analysis_monthly_ceiling_usd" {
  description = "Gate 21.2 configured monthly ceiling; this is CONFIGURED_LIMIT, not measured spend."
  value       = var.public_analysis_monthly_ceiling_usd
}

output "public_analysis_cost_ceiling_materialized" {
  description = "Whether the Gate 21.2 ceiling and kill switch exist."
  value       = var.public_analysis_cost_ceiling_materialized
}

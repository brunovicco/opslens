variable "agentcore_runtime_experiment_enabled" {
  description = "Create the temporary Phase 14 AgentCore Runtime experiment. Disabled by default."
  type        = bool
  default     = false
}

variable "agentcore_runtime_artifact_version_id" {
  description = "Exact S3 VersionId of the verified content-addressed AgentCore direct-code ZIP."
  type        = string
  default     = null
  nullable    = true
}

locals {
  agentcore_runtime_name                = "opslens_dev_bounded_runtime"
  agentcore_runtime_execution_role_name = "OpsLensAgentCoreRuntimeExecutionRole"
  agentcore_runtime_purpose             = "bounded-agentcore-runtime-experiment"

  agentcore_runtime_artifact_sha256 = (
    "a846034ad646c4f6383ac08e47d9ed065b4a9f3349c14104db49a2d510b3ec88"
  )

  agentcore_runtime_artifact_key = (
    "agentcore/runtime/${local.agentcore_runtime_artifact_sha256}/opslens-agentcore-runtime.zip"
  )

  agentcore_runtime_arn_prefix = (
    "arn:aws:bedrock-agentcore:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:runtime/${local.agentcore_runtime_name}-*"
  )

  agentcore_runtime_log_group_prefix = (
    "/aws/bedrock-agentcore/runtimes/${local.agentcore_runtime_name}-*"
  )

  agentcore_runtime_log_group_arn = (
    "arn:aws:logs:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:log-group:${local.agentcore_runtime_log_group_prefix}"
  )

  agentcore_inference_profile_id = "us.anthropic.claude-haiku-4-5-20251001-v1:0"

  agentcore_inference_profile_arn = (
    "arn:aws:bedrock:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:inference-profile/${local.agentcore_inference_profile_id}"
  )

  agentcore_foundation_model_arns = [
    "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-haiku-4-5-20251001-v1:0",
    "arn:aws:bedrock:us-east-2::foundation-model/anthropic.claude-haiku-4-5-20251001-v1:0",
    "arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-haiku-4-5-20251001-v1:0",
  ]
}

data "aws_iam_policy_document" "agentcore_runtime_assume_role" {
  statement {
    sid     = "AllowAgentCoreRuntimeAssumeRole"
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["bedrock-agentcore.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }

    condition {
      test     = "ArnLike"
      variable = "aws:SourceArn"
      values   = [local.agentcore_runtime_arn_prefix]
    }
  }
}

data "aws_iam_policy_document" "agentcore_runtime_execution" {
  statement {
    sid    = "WriteAgentCoreRuntimeLogs"
    effect = "Allow"

    actions = [
      "logs:CreateLogGroup",
      "logs:DescribeLogStreams",
      "logs:PutResourcePolicy",
    ]

    resources = [
      local.agentcore_runtime_log_group_arn,
    ]
  }

  statement {
    sid     = "DescribeAgentCoreRuntimeLogGroups"
    effect  = "Allow"
    actions = ["logs:DescribeLogGroups"]

    resources = [
      "arn:aws:logs:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:log-group:*",
    ]
  }

  statement {
    sid    = "WriteAgentCoreRuntimeLogStreams"
    effect = "Allow"

    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]

    resources = [
      "${local.agentcore_runtime_log_group_arn}:log-stream:*",
    ]
  }

  statement {
    sid    = "WriteAgentCoreRuntimeTraces"
    effect = "Allow"

    actions = [
      "xray:GetSamplingRules",
      "xray:GetSamplingTargets",
      "xray:PutTelemetryRecords",
      "xray:PutTraceSegments",
    ]

    resources = ["*"]
  }

  statement {
    sid     = "WriteAgentCoreRuntimeMetrics"
    effect  = "Allow"
    actions = ["cloudwatch:PutMetricData"]

    resources = ["*"]

    condition {
      test     = "StringEquals"
      variable = "cloudwatch:namespace"
      values   = ["bedrock-agentcore"]
    }
  }

  statement {
    sid     = "InvokeExactAgentCoreInferenceProfile"
    effect  = "Allow"
    actions = ["bedrock:InvokeModel"]

    resources = [
      local.agentcore_inference_profile_arn,
    ]
  }

  statement {
    sid     = "InvokeExactAgentCoreGeoDestinationModels"
    effect  = "Allow"
    actions = ["bedrock:InvokeModel"]

    resources = local.agentcore_foundation_model_arns

    condition {
      test     = "StringEquals"
      variable = "bedrock:InferenceProfileArn"
      values   = [local.agentcore_inference_profile_arn]
    }
  }
}

resource "aws_iam_role" "agentcore_runtime_execution" {
  count = var.agentcore_runtime_experiment_enabled ? 1 : 0

  name               = local.agentcore_runtime_execution_role_name
  assume_role_policy = data.aws_iam_policy_document.agentcore_runtime_assume_role.json

  tags = {
    Purpose = "bounded-agentcore-runtime-execution"
  }
}

resource "aws_iam_role_policy" "agentcore_runtime_execution" {
  count = var.agentcore_runtime_experiment_enabled ? 1 : 0

  name   = "OpsLensAgentCoreRuntimeExecutionPolicy"
  role   = aws_iam_role.agentcore_runtime_execution[0].id
  policy = data.aws_iam_policy_document.agentcore_runtime_execution.json
}

resource "aws_bedrockagentcore_agent_runtime" "bounded_experiment" {
  count = var.agentcore_runtime_experiment_enabled ? 1 : 0

  agent_runtime_name = local.agentcore_runtime_name
  description        = "Temporary Phase 14 bounded AgentCore Runtime experiment."
  role_arn           = aws_iam_role.agentcore_runtime_execution[0].arn

  agent_runtime_artifact {
    code_configuration {
      entry_point = ["main.py"]
      runtime     = "PYTHON_3_13"

      code {
        s3 {
          bucket     = aws_s3_bucket.deployment_artifacts.id
          prefix     = local.agentcore_runtime_artifact_key
          version_id = var.agentcore_runtime_artifact_version_id
        }
      }
    }
  }

  network_configuration {
    # PUBLIC is an ADR 0053 time-bounded dev experiment exception, not a production posture.
    network_mode = "PUBLIC"
  }

  protocol_configuration {
    server_protocol = "HTTP"
  }

  lifecycle_configuration {
    idle_runtime_session_timeout = 120
    max_lifetime                 = 900
  }

  tags = {
    Purpose = local.agentcore_runtime_purpose
  }

  lifecycle {
    precondition {
      condition = (
        !var.agentcore_runtime_experiment_enabled ||
        try(length(trimspace(var.agentcore_runtime_artifact_version_id)), 0) > 0
      )
      error_message = "agentcore_runtime_artifact_version_id is required when the experiment is enabled."
    }
  }

  depends_on = [
    aws_iam_role_policy.agentcore_runtime_execution,
  ]
}

output "agentcore_runtime_experiment" {
  description = "Bounded metadata for the temporary AgentCore Runtime experiment when enabled."
  value = var.agentcore_runtime_experiment_enabled ? {
    arn                 = aws_bedrockagentcore_agent_runtime.bounded_experiment[0].agent_runtime_arn
    id                  = aws_bedrockagentcore_agent_runtime.bounded_experiment[0].agent_runtime_id
    version             = aws_bedrockagentcore_agent_runtime.bounded_experiment[0].agent_runtime_version
    artifact_key        = local.agentcore_runtime_artifact_key
    artifact_sha256     = local.agentcore_runtime_artifact_sha256
    artifact_version_id = var.agentcore_runtime_artifact_version_id
    execution_role_arn  = aws_iam_role.agentcore_runtime_execution[0].arn
    network_mode        = "PUBLIC"
    protocol            = "HTTP"
  } : null
}

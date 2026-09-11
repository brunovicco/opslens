data "aws_iam_policy_document" "public_async_lambda_assume_role" {
  statement {
    sid     = "AllowLambdaService"
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type = "Service"
      identifiers = [
        "lambda.amazonaws.com",
      ]
    }
  }
}

resource "aws_iam_role" "public_async_api" {
  count = local.public_async_runtime_count

  name        = local.public_async_api_role_name
  description = "Execution role for the disabled Gate 19.4 public-analysis API Lambda."

  assume_role_policy = data.aws_iam_policy_document.public_async_lambda_assume_role.json

  tags = {
    Purpose = "public-analysis-api-runtime"
    Gate    = "19.4"
  }
}

data "aws_iam_policy_document" "public_async_api_runtime" {
  count = local.public_async_runtime_count

  statement {
    sid    = "PublishAdmittedJobs"
    effect = "Allow"

    actions = [
      "sqs:SendMessage",
    ]

    resources = [
      aws_sqs_queue.public_async_job_queue[0].arn,
    ]
  }

  statement {
    sid    = "ReadWriteJobAuthority"
    effect = "Allow"

    actions = [
      "dynamodb:GetItem",
      "dynamodb:PutItem",
      "dynamodb:UpdateItem",
      "dynamodb:TransactWriteItems",
    ]

    resources = [
      aws_dynamodb_table.public_async_jobs[0].arn,
    ]
  }

  statement {
    sid    = "WriteApiLambdaLogs"
    effect = "Allow"

    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]

    resources = [
      "${aws_cloudwatch_log_group.public_async_api[0].arn}:*",
    ]
  }

  statement {
    sid    = "WriteApiXRayTelemetry"
    effect = "Allow"

    actions = [
      "xray:PutTelemetryRecords",
      "xray:PutTraceSegments",
    ]

    resources = [
      "*",
    ]
  }
}

resource "aws_iam_role_policy" "public_async_api" {
  count = local.public_async_runtime_count

  name = "OpsLensPublicAnalysisApiRuntimeAccess"
  role = aws_iam_role.public_async_api[0].id

  policy = data.aws_iam_policy_document.public_async_api_runtime[0].json
}

resource "aws_iam_role" "public_async_worker" {
  count = local.public_async_runtime_count

  name        = local.public_async_worker_role_name
  description = "Execution role for the disabled Gate 19.4 public-analysis worker Lambda."

  assume_role_policy = data.aws_iam_policy_document.public_async_lambda_assume_role.json

  tags = {
    Purpose = "public-analysis-worker-runtime"
    Gate    = "19.4"
  }
}

data "aws_iam_policy_document" "public_async_worker_runtime" {
  count = local.public_async_runtime_count

  statement {
    sid    = "ConsumeAdmittedJobs"
    effect = "Allow"

    actions = [
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:ChangeMessageVisibility",
      "sqs:GetQueueAttributes",
    ]

    resources = [
      aws_sqs_queue.public_async_job_queue[0].arn,
    ]
  }

  statement {
    sid    = "ReadWriteWorkerJobAuthority"
    effect = "Allow"

    actions = [
      "dynamodb:GetItem",
      "dynamodb:UpdateItem",
    ]

    resources = [
      aws_dynamodb_table.public_async_jobs[0].arn,
    ]
  }

  statement {
    sid    = "RetrieveRetainedKnowledgeBase"
    effect = "Allow"

    actions = [
      "bedrock:Retrieve",
    ]

    resources = [
      local.public_async_knowledge_base_arn,
    ]
  }

  statement {
    sid    = "InvokeRetainedSynthesisModel"
    effect = "Allow"

    actions = [
      "bedrock:InvokeModel",
    ]

    resources = concat(
      [local.public_async_inference_profile_arn],
      local.public_async_foundation_model_arns,
    )
  }

  statement {
    sid    = "WriteWorkerLambdaLogs"
    effect = "Allow"

    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]

    resources = [
      "${aws_cloudwatch_log_group.public_async_worker[0].arn}:*",
    ]
  }

  statement {
    sid    = "WriteWorkerXRayTelemetry"
    effect = "Allow"

    actions = [
      "xray:PutTelemetryRecords",
      "xray:PutTraceSegments",
    ]

    resources = [
      "*",
    ]
  }
}

resource "aws_iam_role_policy" "public_async_worker" {
  count = local.public_async_runtime_count

  name = "OpsLensPublicAnalysisWorkerRuntimeAccess"
  role = aws_iam_role.public_async_worker[0].id

  policy = data.aws_iam_policy_document.public_async_worker_runtime[0].json
}

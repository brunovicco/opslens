variable "public_async_runtime_materialized" {
  description = "Materialize the Gate 19.4 async runtime resources. Disabled by default and not deployment authority."
  type        = bool
  default     = false
}

variable "public_async_api_artifact_key" {
  description = "S3 key of the verified API Lambda ZIP when the disabled runtime is intentionally materialized."
  type        = string
  default     = null
  nullable    = true
}

variable "public_async_api_artifact_version_id" {
  description = "Exact S3 VersionId of the verified API Lambda ZIP when materialized."
  type        = string
  default     = null
  nullable    = true
}

variable "public_async_api_source_code_hash" {
  description = "Base64 SHA-256 of the verified API Lambda ZIP when materialized."
  type        = string
  default     = null
  nullable    = true
}

variable "public_async_worker_artifact_key" {
  description = "S3 key of the verified worker Lambda ZIP when the disabled runtime is intentionally materialized."
  type        = string
  default     = null
  nullable    = true
}

variable "public_async_worker_artifact_version_id" {
  description = "Exact S3 VersionId of the verified worker Lambda ZIP when materialized."
  type        = string
  default     = null
  nullable    = true
}

variable "public_async_worker_source_code_hash" {
  description = "Base64 SHA-256 of the verified worker Lambda ZIP when materialized."
  type        = string
  default     = null
  nullable    = true
}

locals {
  public_async_runtime_count = var.public_async_runtime_materialized ? 1 : 0

  public_async_job_table_name = "opslens-dev-public-analysis-jobs"
  public_async_job_queue_name = "opslens-dev-public-analysis-jobs"
  public_async_job_dlq_name   = "opslens-dev-public-analysis-jobs-dlq"

  public_async_api_function_name    = "opslens-dev-public-analysis-api"
  public_async_worker_function_name = "opslens-dev-public-analysis-worker"

  public_async_api_log_group_name = (
    "/aws/lambda/${local.public_async_api_function_name}"
  )
  public_async_worker_log_group_name = (
    "/aws/lambda/${local.public_async_worker_function_name}"
  )
  public_async_access_log_group_name = "/aws/apigateway/opslens-dev-public-analysis"

  public_async_api_role_name    = "OpsLensPublicAnalysisApiRole"
  public_async_worker_role_name = "OpsLensPublicAnalysisWorkerRole"

  public_async_knowledge_base_id = "BTVJ2PBR2A"
  public_async_model_id          = "us.anthropic.claude-haiku-4-5-20251001-v1:0"

  public_async_knowledge_base_arn = (
    "arn:aws:bedrock:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:knowledge-base/${local.public_async_knowledge_base_id}"
  )
  public_async_inference_profile_arn = (
    "arn:aws:bedrock:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:inference-profile/${local.public_async_model_id}"
  )
  public_async_foundation_model_arns = [
    "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-haiku-4-5-20251001-v1:0",
    "arn:aws:bedrock:us-east-2::foundation-model/anthropic.claude-haiku-4-5-20251001-v1:0",
    "arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-haiku-4-5-20251001-v1:0",
  ]

  public_async_submission_lease_seconds = 30
  public_async_worker_lease_seconds     = 90
  public_async_max_attempts             = 3
  public_async_worker_timeout_seconds   = 60
  public_async_queue_visibility_seconds = 120
  public_async_redrive_receive_count    = 4
}

resource "aws_dynamodb_table" "public_async_jobs" {
  count = local.public_async_runtime_count

  name         = local.public_async_job_table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"

  deletion_protection_enabled = true

  attribute {
    name = "pk"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = {
    Purpose = "public-analysis-job-authority"
    Gate    = "19.4"
  }
}

resource "aws_sqs_queue" "public_async_job_dlq" {
  count = local.public_async_runtime_count

  name                      = local.public_async_job_dlq_name
  message_retention_seconds = 1209600
  sqs_managed_sse_enabled   = true

  tags = {
    Purpose = "public-analysis-job-dead-letter"
    Gate    = "19.4"
  }
}

resource "aws_sqs_queue" "public_async_job_queue" {
  count = local.public_async_runtime_count

  name                       = local.public_async_job_queue_name
  visibility_timeout_seconds = local.public_async_queue_visibility_seconds
  message_retention_seconds  = 86400
  receive_wait_time_seconds  = 20
  sqs_managed_sse_enabled    = true

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.public_async_job_dlq[0].arn
    maxReceiveCount     = local.public_async_redrive_receive_count
  })

  tags = {
    Purpose = "public-analysis-job-backpressure"
    Gate    = "19.4"
  }
}

resource "aws_sqs_queue_redrive_allow_policy" "public_async_job_dlq" {
  count = local.public_async_runtime_count

  queue_url = aws_sqs_queue.public_async_job_dlq[0].id
  redrive_allow_policy = jsonencode({
    redrivePermission = "byQueue"
    sourceQueueArns = [
      aws_sqs_queue.public_async_job_queue[0].arn,
    ]
  })
}

resource "aws_lambda_function" "public_async_api" {
  count = local.public_async_runtime_count

  # checkov:skip=CKV_AWS_116: The API path is synchronous control-plane work; queue publication failures are persisted in deterministic job state rather than a Lambda DLQ.
  # checkov:skip=CKV_AWS_117: The API Lambda needs only AWS public service endpoints and no private VPC resources; VPC attachment would add NAT complexity without a retained requirement.
  # checkov:skip=CKV_AWS_173: Environment variables contain only non-secret resource coordinates and disabled/configured-limit flags.
  # checkov:skip=CKV_AWS_272: Code signing remains deferred until OpsLens has an artifact-signing trust workflow; exact S3 VersionId and source hash are required before materialization.

  function_name = local.public_async_api_function_name
  description   = "Disabled Gate 19.4 async submit/status/result control path."
  role          = aws_iam_role.public_async_api[0].arn

  runtime       = "python3.13"
  architectures = ["x86_64"]
  handler       = "opslens.public_analysis.async_lambda.api_lambda_handler"

  s3_bucket         = aws_s3_bucket.deployment_artifacts.bucket
  s3_key            = var.public_async_api_artifact_key
  s3_object_version = var.public_async_api_artifact_version_id
  source_code_hash  = var.public_async_api_source_code_hash

  memory_size                    = 512
  timeout                        = 15
  reserved_concurrent_executions = 2

  environment {
    variables = {
      OPSLENS_ASYNC_JOB_TABLE_NAME           = aws_dynamodb_table.public_async_jobs[0].name
      OPSLENS_ASYNC_JOB_QUEUE_URL            = aws_sqs_queue.public_async_job_queue[0].url
      OPSLENS_ASYNC_SUBMIT_ENABLED           = "false"
      OPSLENS_ASYNC_SUBMISSION_LEASE_SECONDS = tostring(local.public_async_submission_lease_seconds)
    }
  }

  tracing_config {
    mode = "Active"
  }

  logging_config {
    log_format            = "JSON"
    application_log_level = "INFO"
    system_log_level      = "INFO"
    log_group             = aws_cloudwatch_log_group.public_async_api[0].name
  }

  lifecycle {
    precondition {
      condition = (
        var.public_async_api_artifact_key != null &&
        var.public_async_api_artifact_version_id != null &&
        var.public_async_api_source_code_hash != null
      )
      error_message = "Materializing the public async API requires an exact artifact key, VersionId, and source hash."
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.public_async_api,
    aws_iam_role_policy.public_async_api,
  ]

  tags = {
    Purpose = "public-analysis-api-control-path"
    Gate    = "19.4"
  }
}

resource "aws_lambda_function" "public_async_worker" {
  count = local.public_async_runtime_count

  # checkov:skip=CKV_AWS_116: SQS owns redrive to the dedicated DLQ; adding a Lambda DLQ would create a second failure authority.
  # checkov:skip=CKV_AWS_117: The retained worker dependencies are public GitHub and AWS service endpoints; no private VPC resource is required.
  # checkov:skip=CKV_AWS_173: Environment variables contain only non-secret exact resource coordinates and disabled/configured-limit flags.
  # checkov:skip=CKV_AWS_272: Code signing remains deferred until OpsLens has an artifact-signing trust workflow; exact S3 VersionId and source hash are required before materialization.

  function_name = local.public_async_worker_function_name
  description   = "Disabled Gate 19.4 public-analysis SQS worker."
  role          = aws_iam_role.public_async_worker[0].arn

  runtime       = "python3.13"
  architectures = ["x86_64"]
  handler       = "opslens.public_analysis.async_lambda.worker_lambda_handler"

  s3_bucket         = aws_s3_bucket.deployment_artifacts.bucket
  s3_key            = var.public_async_worker_artifact_key
  s3_object_version = var.public_async_worker_artifact_version_id
  source_code_hash  = var.public_async_worker_source_code_hash

  memory_size                    = 1024
  timeout                        = local.public_async_worker_timeout_seconds
  reserved_concurrent_executions = 0

  environment {
    variables = {
      OPSLENS_ASYNC_JOB_TABLE_NAME       = aws_dynamodb_table.public_async_jobs[0].name
      OPSLENS_ASYNC_JOB_QUEUE_ARN        = aws_sqs_queue.public_async_job_queue[0].arn
      OPSLENS_ASYNC_WORKER_ENABLED       = "false"
      OPSLENS_ASYNC_WORKER_LEASE_SECONDS = tostring(local.public_async_worker_lease_seconds)
      OPSLENS_ASYNC_MAX_ATTEMPTS         = tostring(local.public_async_max_attempts)
    }
  }

  tracing_config {
    mode = "Active"
  }

  logging_config {
    log_format            = "JSON"
    application_log_level = "INFO"
    system_log_level      = "INFO"
    log_group             = aws_cloudwatch_log_group.public_async_worker[0].name
  }

  lifecycle {
    precondition {
      condition = (
        var.public_async_worker_artifact_key != null &&
        var.public_async_worker_artifact_version_id != null &&
        var.public_async_worker_source_code_hash != null
      )
      error_message = "Materializing the public async worker requires an exact artifact key, VersionId, and source hash."
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.public_async_worker,
    aws_iam_role_policy.public_async_worker,
  ]

  tags = {
    Purpose = "public-analysis-worker"
    Gate    = "19.4"
  }
}

resource "aws_lambda_event_source_mapping" "public_async_worker" {
  count = local.public_async_runtime_count

  event_source_arn = aws_sqs_queue.public_async_job_queue[0].arn
  function_name    = aws_lambda_function.public_async_worker[0].arn

  enabled                            = false
  batch_size                         = 1
  maximum_batching_window_in_seconds = 0
  function_response_types            = ["ReportBatchItemFailures"]
}

resource "aws_apigatewayv2_api" "public_async" {
  count = local.public_async_runtime_count

  name          = "opslens-dev-public-analysis"
  protocol_type = "HTTP"
  description   = "Gate 19.4 async public-analysis API with execute-api endpoint disabled."

  disable_execute_api_endpoint = true

  tags = {
    Purpose = "public-analysis-http-contract"
    Gate    = "19.4"
  }
}

resource "aws_apigatewayv2_integration" "public_async_api_lambda" {
  count = local.public_async_runtime_count

  api_id = aws_apigatewayv2_api.public_async[0].id

  integration_type       = "AWS_PROXY"
  integration_method     = "POST"
  integration_uri        = aws_lambda_function.public_async_api[0].invoke_arn
  payload_format_version = "2.0"
  timeout_milliseconds   = 10000
}

resource "aws_apigatewayv2_route" "public_async_submit" {
  count = local.public_async_runtime_count

  api_id             = aws_apigatewayv2_api.public_async[0].id
  route_key          = "POST /v1/analyses"
  authorization_type = "NONE"
  target             = "integrations/${aws_apigatewayv2_integration.public_async_api_lambda[0].id}"
}

resource "aws_apigatewayv2_route" "public_async_status" {
  count = local.public_async_runtime_count

  api_id             = aws_apigatewayv2_api.public_async[0].id
  route_key          = "GET /v1/analyses/{job_id}"
  authorization_type = "NONE"
  target             = "integrations/${aws_apigatewayv2_integration.public_async_api_lambda[0].id}"
}

resource "aws_apigatewayv2_route" "public_async_result" {
  count = local.public_async_runtime_count

  api_id             = aws_apigatewayv2_api.public_async[0].id
  route_key          = "GET /v1/analyses/{job_id}/result"
  authorization_type = "NONE"
  target             = "integrations/${aws_apigatewayv2_integration.public_async_api_lambda[0].id}"
}

resource "aws_apigatewayv2_stage" "public_async_default" {
  count = local.public_async_runtime_count

  api_id = aws_apigatewayv2_api.public_async[0].id
  name   = "$default"

  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.public_async_access[0].arn
    format = jsonencode({
      requestId        = "$context.requestId"
      routeKey         = "$context.routeKey"
      status           = "$context.status"
      responseLength   = "$context.responseLength"
      integrationError = "$context.integrationErrorMessage"
    })
  }

  default_route_settings {
    detailed_metrics_enabled = true
    throttling_burst_limit   = 10
    throttling_rate_limit    = 5
  }

  tags = {
    Purpose = "public-analysis-disabled-stage"
    Gate    = "19.4"
  }
}

resource "aws_lambda_permission" "public_async_api_gateway" {
  count = local.public_async_runtime_count

  statement_id  = "AllowExecutionFromApiGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.public_async_api[0].function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.public_async[0].execution_arn}/*/*"
}

output "public_async_runtime_materialized" {
  description = "Whether Gate 19.4 async resources are selected for materialization; default false is a configured state, not utilization evidence."
  value       = var.public_async_runtime_materialized
}

output "public_async_execute_api_endpoint_disabled" {
  description = "Gate 19.4 keeps the execute-api endpoint disabled whenever the topology is materialized."
  value       = true
}

output "public_async_submit_enabled" {
  description = "New-job admission remains disabled in Gate 19.4."
  value       = false
}

output "public_async_worker_event_source_enabled" {
  description = "SQS-to-worker dispatch remains disabled in Gate 19.4."
  value       = false
}

output "public_async_worker_reserved_concurrency" {
  description = "Configured worker reserved concurrency for Gate 19.4; this is CONFIGURED_LIMIT, not measured utilization."
  value       = 0
}

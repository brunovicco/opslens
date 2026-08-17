resource "aws_lambda_function_event_invoke_config" "kev_ingestion" {
  function_name = aws_lambda_function.kev_ingestion.function_name

  maximum_event_age_in_seconds = 3600
  maximum_retry_attempts       = 2

  destination_config {
    on_failure {
      destination = aws_sqs_queue.kev_ingestion_failures.arn
    }
  }

  depends_on = [
    aws_iam_role_policy.kev_lambda_runtime,
  ]
}

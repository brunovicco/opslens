resource "aws_lambda_permission" "epss_silver_from_s3" {
  statement_id  = "AllowS3InvokeEpssSilver"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.epss_silver.function_name
  principal     = "s3.amazonaws.com"

  source_arn     = aws_s3_bucket.data.arn
  source_account = data.aws_caller_identity.current.account_id
}

resource "aws_lambda_permission" "kev_silver_from_s3" {
  statement_id  = "AllowS3InvokeKevSilver"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.kev_silver.function_name
  principal     = "s3.amazonaws.com"

  source_arn     = aws_s3_bucket.data.arn
  source_account = data.aws_caller_identity.current.account_id
}

resource "aws_lambda_permission" "nvd_silver_from_s3" {
  statement_id  = "AllowS3InvokeNvdSilver"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.nvd_silver.function_name
  principal     = "s3.amazonaws.com"

  source_arn     = aws_s3_bucket.data.arn
  source_account = data.aws_caller_identity.current.account_id
}

resource "aws_lambda_permission" "nvd_promotion_from_s3" {
  statement_id  = "AllowS3InvokeNvdPromotion"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.nvd_promotion.function_name
  principal     = "s3.amazonaws.com"

  source_arn     = aws_s3_bucket.data.arn
  source_account = data.aws_caller_identity.current.account_id
}

resource "aws_lambda_function_event_invoke_config" "epss_silver" {
  function_name = aws_lambda_function.epss_silver.function_name

  maximum_event_age_in_seconds = 3600
  maximum_retry_attempts       = 2

  destination_config {
    on_failure {
      destination = aws_sqs_queue.epss_silver_failures.arn
    }
  }

  depends_on = [
    aws_iam_role_policy.epss_silver_lambda_runtime,
  ]
}

resource "aws_s3_bucket_notification" "epss_silver" {
  bucket = aws_s3_bucket.data.id

  lambda_function {
    id = "epss-silver-bronze-object-created"

    lambda_function_arn = aws_lambda_function.epss_silver.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "bronze/epss/"
  }

  lambda_function {
    id = "kev-silver-bronze-object-created"

    lambda_function_arn = aws_lambda_function.kev_silver.arn
    events              = ["s3:ObjectCreated:Put"]
    filter_prefix       = "bronze/kev/"
    filter_suffix       = "known_exploited_vulnerabilities.json"
  }

  lambda_function {
    id = "nvd-silver-bootstrap-complete-created"

    lambda_function_arn = aws_lambda_function.nvd_silver.arn
    events              = ["s3:ObjectCreated:Put"]
    filter_prefix       = "bronze/nvd/cve/bootstrap/"
    filter_suffix       = "manifest.json"
  }

  lambda_function {
    id = "nvd-silver-incremental-complete-created"

    lambda_function_arn = aws_lambda_function.nvd_silver.arn
    events              = ["s3:ObjectCreated:Put"]
    filter_prefix       = "bronze/nvd/cve/updates/"
    filter_suffix       = "manifest.json"
  }

  lambda_function {
    id = "nvd-promotion-silver-complete-created"

    lambda_function_arn = aws_lambda_function.nvd_promotion.arn
    events              = ["s3:ObjectCreated:Put"]
    filter_prefix       = "silver/nvd/cve/schema_version%3D1/source_kind%3Dincremental/"
    filter_suffix       = "manifest.json"
  }

  depends_on = [
    aws_lambda_permission.epss_silver_from_s3,
    aws_lambda_permission.kev_silver_from_s3,
    aws_lambda_permission.nvd_silver_from_s3,
    aws_lambda_permission.nvd_promotion_from_s3,
  ]
}

resource "aws_lambda_permission" "epss_silver_from_s3" {
  statement_id  = "AllowS3InvokeEpssSilver"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.epss_silver.function_name
  principal     = "s3.amazonaws.com"

  source_arn     = aws_s3_bucket.data.arn
  source_account = data.aws_caller_identity.current.account_id
}

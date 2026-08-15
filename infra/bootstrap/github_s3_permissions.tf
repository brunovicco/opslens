locals {
  dev_data_bucket_name = "opslens-dev-data-${data.aws_caller_identity.current.account_id}-${var.aws_region}"
  dev_data_bucket_arn  = "arn:aws:s3:::${local.dev_data_bucket_name}"

  dev_artifacts_bucket_name = "opslens-dev-artifacts-${data.aws_caller_identity.current.account_id}-${var.aws_region}"
  dev_artifacts_bucket_arn  = "arn:aws:s3:::${local.dev_artifacts_bucket_name}"
}

data "aws_iam_policy_document" "github_actions_s3_data_lake" {
  statement {
    sid    = "ManageOpsLensDevDataBucket"
    effect = "Allow"

    actions = [
      "s3:CreateBucket",
      "s3:DeleteBucket",
      "s3:ListBucket",
      "s3:GetBucketLocation",

      "s3:GetBucketTagging",
      "s3:PutBucketTagging",

      "s3:GetBucketVersioning",
      "s3:PutBucketVersioning",

      "s3:GetBucketPublicAccessBlock",
      "s3:PutBucketPublicAccessBlock",

      "s3:GetEncryptionConfiguration",
      "s3:PutEncryptionConfiguration",

      "s3:GetBucketOwnershipControls",
      "s3:PutBucketOwnershipControls",

      "s3:GetLifecycleConfiguration",
      "s3:PutLifecycleConfiguration",

      "s3:GetBucketPolicy",
      "s3:GetBucketPolicyStatus",
      "s3:PutBucketPolicy",
      "s3:DeleteBucketPolicy",

      "s3:GetBucketAcl",

      "s3:TagResource",
      "s3:UntagResource",
      "s3:ListTagsForResource",

      # Required by aws_s3_bucket read-after-create and refresh.
      "s3:GetBucketCORS",
      "s3:GetBucketWebsite",
      "s3:GetAccelerateConfiguration",
      "s3:GetBucketRequestPayment",
      "s3:GetBucketLogging",
      "s3:GetReplicationConfiguration",
      "s3:GetBucketObjectLockConfiguration",
    ]

    resources = [
      local.dev_data_bucket_arn,
      local.dev_artifacts_bucket_arn,
    ]
  }

  statement {
    sid    = "ManageOpsLensDevDeploymentArtifacts"
    effect = "Allow"

    actions = [
      "s3:PutObject",
      "s3:GetObject",
      "s3:GetObjectVersion",
    ]

    resources = [
      "${local.dev_artifacts_bucket_arn}/lambda/*",
    ]
  }
}

resource "aws_iam_role_policy" "github_actions_s3_data_lake" {
  name = "OpsLensS3DataLakeDevAccess"
  role = aws_iam_role.github_actions_deploy.id

  policy = data.aws_iam_policy_document.github_actions_s3_data_lake.json
}

locals {
  dev_terraform_state_key = "environments/dev/terraform.tfstate"
}

data "aws_iam_policy_document" "github_actions_terraform_state" {
  statement {
    sid     = "ListDevTerraformState"
    effect  = "Allow"
    actions = ["s3:ListBucket"]

    resources = [
      aws_s3_bucket.terraform_state.arn,
    ]

    condition {
      test     = "StringEquals"
      variable = "s3:prefix"

      values = [
        local.dev_terraform_state_key,
      ]
    }
  }

  statement {
    sid    = "ReadWriteDevTerraformState"
    effect = "Allow"

    actions = [
      "s3:GetObject",
      "s3:PutObject",
    ]

    resources = [
      "${aws_s3_bucket.terraform_state.arn}/${local.dev_terraform_state_key}",
    ]
  }

  statement {
    sid    = "ManageDevTerraformStateLock"
    effect = "Allow"

    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
    ]

    resources = [
      "${aws_s3_bucket.terraform_state.arn}/${local.dev_terraform_state_key}.tflock",
    ]
  }
}

resource "aws_iam_role_policy" "github_actions_terraform_state" {
  name = "OpsLensTerraformStateDevAccess"
  role = aws_iam_role.github_actions_deploy.id

  policy = data.aws_iam_policy_document.github_actions_terraform_state.json
}

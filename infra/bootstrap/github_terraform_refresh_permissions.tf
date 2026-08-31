locals {
  github_terraform_refresh_oidc_provider_arn = (
    "arn:aws:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/token.actions.githubusercontent.com"
  )

  github_terraform_refresh_role_names = [
    "OpsLensGhsaBronzeLambdaRole",
    "OpsLensGhsaSilverLambdaRole",
    "OpsLensKevSilverLambdaRole",
    "OpsLensNvdBootstrapIngestionLambdaRole",
    "OpsLensNvdIncrementalLambdaRole",
    "OpsLensNvdSilverLambdaRole",
  ]

  github_terraform_refresh_role_arns = [
    for role_name in local.github_terraform_refresh_role_names :
    "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${role_name}"
  ]

  github_terraform_refresh_log_group_names = [
    "/aws/lambda/opslens-dev-ghsa-bronze",
    "/aws/lambda/opslens-dev-ghsa-silver",
    "/aws/lambda/opslens-dev-kev-silver",
    "/aws/lambda/opslens-dev-nvd-bootstrap-ingestion",
    "/aws/lambda/opslens-dev-nvd-incremental",
    "/aws/lambda/opslens-dev-nvd-silver",
  ]

  github_terraform_refresh_log_group_arns = [
    for log_group_name in local.github_terraform_refresh_log_group_names :
    "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:${log_group_name}"
  ]

  github_terraform_refresh_queue_names = [
    "opslens-dev-kev-silver-failures",
    "opslens-dev-nvd-silver-failures",
  ]

  github_terraform_refresh_queue_arns = [
    for queue_name in local.github_terraform_refresh_queue_names :
    "arn:aws:sqs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:${queue_name}"
  ]

  github_terraform_refresh_ghsa_secret_arn = (
    # Secrets Manager appends a hyphen and six generated characters to the ARN.
    "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:opslens/dev/ghsa/github-token-*"
  )
}

data "aws_iam_policy_document" "github_actions_terraform_refresh" {
  statement {
    sid     = "ReadGitHubActionsOidcProvider"
    effect  = "Allow"
    actions = ["iam:GetOpenIDConnectProvider"]

    resources = [
      local.github_terraform_refresh_oidc_provider_arn,
    ]
  }

  statement {
    sid    = "ReadLegacyRuntimeRoles"
    effect = "Allow"

    # aws_iam_role refresh reads both deprecated aggregate policy attributes;
    # aws_iam_role_policy also requires GetRolePolicy for its own refresh.
    actions = [
      "iam:GetRole",
      "iam:GetRolePolicy",
      "iam:ListAttachedRolePolicies",
      "iam:ListRolePolicies",
    ]

    resources = local.github_terraform_refresh_role_arns
  }

  statement {
    sid     = "ReadLegacyRuntimeLogGroupTags"
    effect  = "Allow"
    actions = ["logs:ListTagsForResource"]

    resources = local.github_terraform_refresh_log_group_arns
  }

  statement {
    sid    = "ReadGhsaSecretMetadata"
    effect = "Allow"

    actions = [
      "secretsmanager:DescribeSecret",
      "secretsmanager:GetResourcePolicy",
    ]

    resources = [
      local.github_terraform_refresh_ghsa_secret_arn,
    ]
  }

  statement {
    sid    = "ReadLegacyFailureQueueAttributes"
    effect = "Allow"

    actions = [
      "sqs:GetQueueAttributes",
      "sqs:ListQueueTags",
    ]

    resources = local.github_terraform_refresh_queue_arns
  }
}

resource "aws_iam_policy" "github_actions_terraform_refresh" {
  name        = "OpsLensTerraformRefreshDevAccess"
  description = "Allow OpsLens GitHub deployment automation to refresh legacy dev resources."

  policy = data.aws_iam_policy_document.github_actions_terraform_refresh.json
}

resource "aws_iam_role_policy_attachment" "github_actions_terraform_refresh" {
  role       = aws_iam_role.github_actions_deploy.name
  policy_arn = aws_iam_policy.github_actions_terraform_refresh.arn
}

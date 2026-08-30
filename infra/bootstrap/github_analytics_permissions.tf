locals {
  dev_analytics_glue_database_name   = "opslens_dev"
  dev_analytics_glue_epss_table_name = "epss_scores"
  dev_analytics_glue_kev_table_name  = "kev_entries"
  dev_analytics_glue_nvd_table_name  = "nvd_cve_versions"
  dev_analytics_glue_ghsa_table_name = "ghsa_advisory_versions"
  dev_analytics_athena_workgroup     = "opslens-dev"

  dev_analytics_glue_catalog_arn = (
    "arn:aws:glue:${var.aws_region}:${data.aws_caller_identity.current.account_id}:catalog"
  )

  dev_analytics_glue_database_arn = (
    "arn:aws:glue:${var.aws_region}:${data.aws_caller_identity.current.account_id}:database/${local.dev_analytics_glue_database_name}"
  )

  dev_analytics_glue_epss_table_arn = (
    "arn:aws:glue:${var.aws_region}:${data.aws_caller_identity.current.account_id}:table/${local.dev_analytics_glue_database_name}/${local.dev_analytics_glue_epss_table_name}"
  )

  dev_analytics_glue_kev_table_arn = (
    "arn:aws:glue:${var.aws_region}:${data.aws_caller_identity.current.account_id}:table/${local.dev_analytics_glue_database_name}/${local.dev_analytics_glue_kev_table_name}"
  )

  dev_analytics_glue_nvd_table_arn = (
    "arn:aws:glue:${var.aws_region}:${data.aws_caller_identity.current.account_id}:table/${local.dev_analytics_glue_database_name}/${local.dev_analytics_glue_nvd_table_name}"
  )

  dev_analytics_glue_ghsa_table_arn = (
    "arn:aws:glue:${var.aws_region}:${data.aws_caller_identity.current.account_id}:table/${local.dev_analytics_glue_database_name}/${local.dev_analytics_glue_ghsa_table_name}"
  )

  dev_analytics_glue_database_tables_arn = (
    "arn:aws:glue:${var.aws_region}:${data.aws_caller_identity.current.account_id}:table/${local.dev_analytics_glue_database_name}/*"
  )

  dev_analytics_glue_database_udfs_arn = (
    "arn:aws:glue:${var.aws_region}:${data.aws_caller_identity.current.account_id}:userDefinedFunction/${local.dev_analytics_glue_database_name}/*"
  )

  dev_analytics_athena_workgroup_arn = (
    "arn:aws:athena:${var.aws_region}:${data.aws_caller_identity.current.account_id}:workgroup/${local.dev_analytics_athena_workgroup}"
  )
}

data "aws_iam_policy_document" "github_actions_analytics" {
  statement {
    sid    = "ManageOpsLensGlueDatabase"
    effect = "Allow"

    actions = [
      "glue:CreateDatabase",
      "glue:GetDatabase",
      "glue:GetTags",
      "glue:TagResource",
      "glue:UntagResource",
      "glue:UpdateDatabase",
    ]

    resources = [
      local.dev_analytics_glue_catalog_arn,
      local.dev_analytics_glue_database_arn,
    ]
  }

  statement {
    sid    = "DeleteOpsLensGlueDatabase"
    effect = "Allow"

    actions = [
      "glue:DeleteDatabase",
    ]

    resources = [
      local.dev_analytics_glue_catalog_arn,
      local.dev_analytics_glue_database_arn,
      local.dev_analytics_glue_database_tables_arn,
      local.dev_analytics_glue_database_udfs_arn,
    ]
  }

  statement {
    sid    = "ManageOpsLensGlueEpssTable"
    effect = "Allow"

    actions = [
      "glue:CreateTable",
      "glue:DeleteTable",
      "glue:GetTable",
      "glue:UpdateTable",
    ]

    resources = [
      local.dev_analytics_glue_catalog_arn,
      local.dev_analytics_glue_database_arn,
      local.dev_analytics_glue_epss_table_arn,
    ]
  }

  statement {
    sid    = "ManageOpsLensGlueKevTable"
    effect = "Allow"

    actions = [
      "glue:CreateTable",
      "glue:DeleteTable",
      "glue:GetTable",
      "glue:UpdateTable",
    ]

    resources = [
      local.dev_analytics_glue_catalog_arn,
      local.dev_analytics_glue_database_arn,
      local.dev_analytics_glue_kev_table_arn,
    ]
  }

  statement {
    sid    = "ManageOpsLensGlueNvdTable"
    effect = "Allow"

    actions = [
      "glue:CreateTable",
      "glue:DeleteTable",
      "glue:GetTable",
      "glue:UpdateTable",
    ]

    resources = [
      local.dev_analytics_glue_catalog_arn,
      local.dev_analytics_glue_database_arn,
      local.dev_analytics_glue_nvd_table_arn,
    ]
  }

  statement {
    sid    = "ManageOpsLensGlueGhsaTable"
    effect = "Allow"

    actions = [
      "glue:CreateTable",
      "glue:DeleteTable",
      "glue:GetTable",
      "glue:UpdateTable",
    ]

    resources = [
      local.dev_analytics_glue_catalog_arn,
      local.dev_analytics_glue_database_arn,
      local.dev_analytics_glue_ghsa_table_arn,
    ]
  }

  statement {
    sid    = "ManageOpsLensAthenaWorkgroup"
    effect = "Allow"

    actions = [
      "athena:CreateWorkGroup",
      "athena:DeleteWorkGroup",
      "athena:GetWorkGroup",
      "athena:ListTagsForResource",
      "athena:TagResource",
      "athena:UntagResource",
      "athena:UpdateWorkGroup",
    ]

    resources = [
      local.dev_analytics_athena_workgroup_arn,
    ]
  }
}

resource "aws_iam_policy" "github_actions_analytics" {
  name = "OpsLensAnalyticsDevAccess"

  description = "Allow OpsLens GitHub deployment automation to manage the dev Glue catalog resources and Athena workgroup."

  policy = data.aws_iam_policy_document.github_actions_analytics.json
}

resource "aws_iam_role_policy_attachment" "github_actions_analytics" {
  role = aws_iam_role.github_actions_deploy.name

  policy_arn = aws_iam_policy.github_actions_analytics.arn
}

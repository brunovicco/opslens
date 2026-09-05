locals {
  github_knowledge_base_service_role_name = "OpsLensDevBedrockKnowledgeBaseRole"
  github_knowledge_base_service_role_arn = (
    "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${local.github_knowledge_base_service_role_name}"
  )

  github_knowledge_vector_bucket_name = (
    "opslens-dev-knowledge-${data.aws_caller_identity.current.account_id}-${var.aws_region}"
  )
  github_knowledge_vector_bucket_arn = (
    "arn:aws:s3vectors:${var.aws_region}:${data.aws_caller_identity.current.account_id}:bucket/${local.github_knowledge_vector_bucket_name}"
  )

  github_knowledge_vector_index_name = "opslens-dev-remediation-v1"
  github_knowledge_vector_index_arn = (
    "${local.github_knowledge_vector_bucket_arn}/index/${local.github_knowledge_vector_index_name}"
  )

  github_knowledge_base_arn_pattern = (
    "arn:aws:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:knowledge-base/*"
  )
}

data "aws_iam_policy_document" "github_knowledge_retrieval_deploy" {
  statement {
    sid    = "ManageKnowledgeBaseServiceRole"
    effect = "Allow"

    actions = [
      "iam:CreateRole",
      "iam:DeleteRole",
      "iam:GetRole",
      "iam:GetRolePolicy",
      "iam:ListAttachedRolePolicies",
      "iam:ListInstanceProfilesForRole",
      "iam:ListRolePolicies",
      "iam:ListRoleTags",
      "iam:TagRole",
      "iam:UntagRole",
      "iam:UpdateAssumeRolePolicy",
      "iam:PutRolePolicy",
      "iam:DeleteRolePolicy",
    ]

    resources = [
      local.github_knowledge_base_service_role_arn,
    ]
  }

  statement {
    sid    = "PassKnowledgeBaseServiceRoleToBedrock"
    effect = "Allow"

    actions = [
      "iam:PassRole",
    ]

    resources = [
      local.github_knowledge_base_service_role_arn,
    ]

    condition {
      test     = "StringEquals"
      variable = "iam:PassedToService"

      values = [
        "bedrock.amazonaws.com",
      ]
    }
  }

  # bedrock:CreateKnowledgeBase does not support resource-level authorization
  # because the knowledge-base ARN does not exist before creation. Compensate
  # with exact Region and the required OpsLens Purpose request tag.
  statement {
    sid    = "CreateTaggedKnowledgeBaseInDevRegion"
    effect = "Allow"

    actions = [
      "bedrock:CreateKnowledgeBase",
    ]

    resources = ["*"]

    condition {
      test     = "StringEquals"
      variable = "aws:RequestedRegion"
      values   = [var.aws_region]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:RequestTag/Purpose"
      values   = ["knowledge-retrieval-v1"]
    }
  }

  statement {
    sid    = "ManageTaggedKnowledgeBaseAndDataSource"
    effect = "Allow"

    actions = [
      "bedrock:CreateDataSource",
      "bedrock:DeleteDataSource",
      "bedrock:DeleteKnowledgeBase",
      "bedrock:GetDataSource",
      "bedrock:GetKnowledgeBase",
      "bedrock:ListTagsForResource",
      "bedrock:TagResource",
      "bedrock:UntagResource",
      "bedrock:UpdateDataSource",
      "bedrock:UpdateKnowledgeBase",
    ]

    resources = [
      local.github_knowledge_base_arn_pattern,
    ]

    condition {
      test     = "StringEquals"
      variable = "aws:ResourceTag/Purpose"
      values   = ["knowledge-retrieval-v1"]
    }
  }

  statement {
    sid    = "CreateExactKnowledgeVectorBucket"
    effect = "Allow"

    actions = [
      "s3vectors:CreateVectorBucket",
    ]

    resources = [
      local.github_knowledge_vector_bucket_arn,
    ]

    condition {
      test     = "StringEquals"
      variable = "aws:RequestTag/Purpose"
      values   = ["knowledge-retrieval-vectors"]
    }
  }

  statement {
    sid    = "ManageExactKnowledgeVectorBucket"
    effect = "Allow"

    actions = [
      "s3vectors:DeleteVectorBucket",
      "s3vectors:GetVectorBucket",
      "s3vectors:ListTagsForResource",
      "s3vectors:TagResource",
      "s3vectors:UntagResource",
    ]

    resources = [
      local.github_knowledge_vector_bucket_arn,
    ]
  }

  statement {
    sid    = "CreateExactKnowledgeVectorIndex"
    effect = "Allow"

    actions = [
      "s3vectors:CreateIndex",
    ]

    resources = [
      local.github_knowledge_vector_index_arn,
    ]

    condition {
      test     = "StringEquals"
      variable = "aws:RequestTag/Purpose"
      values   = ["knowledge-retrieval-v1"]
    }
  }

  statement {
    sid    = "ManageExactKnowledgeVectorIndex"
    effect = "Allow"

    actions = [
      "s3vectors:DeleteIndex",
      "s3vectors:GetIndex",
      "s3vectors:ListTagsForResource",
      "s3vectors:TagResource",
      "s3vectors:UntagResource",
    ]

    resources = [
      local.github_knowledge_vector_index_arn,
    ]
  }
}

resource "aws_iam_policy" "github_knowledge_retrieval_deploy" {
  name = "OpsLensGitHubKnowledgeRetrievalDeploy"

  description = (
    "Allow OpsLens GitHub deployment automation to reconcile the bounded Phase 7 knowledge retrieval infrastructure."
  )

  policy = data.aws_iam_policy_document.github_knowledge_retrieval_deploy.json

  tags = {
    Purpose = "github-actions-knowledge-retrieval-deployment"
  }
}

resource "aws_iam_role_policy_attachment" "github_knowledge_retrieval_deploy" {
  role       = aws_iam_role.github_actions_deploy.name
  policy_arn = aws_iam_policy.github_knowledge_retrieval_deploy.arn
}

locals {
  knowledge_publication_prefix = "knowledge/corpus/v1/bedrock"

  knowledge_vector_bucket_name = (
    "opslens-dev-knowledge-${data.aws_caller_identity.current.account_id}-${data.aws_region.current.region}"
  )
  knowledge_vector_index_name = "opslens-dev-remediation-v1"
  knowledge_base_name         = "opslens-dev-remediation-knowledge"
  knowledge_data_source_name  = "opslens-dev-remediation-corpus"
  knowledge_base_role_name    = "OpsLensDevBedrockKnowledgeBaseRole"

  titan_text_embeddings_v2_model_id = "amazon.titan-embed-text-v2:0"
  titan_text_embeddings_v2_model_arn = (
    "arn:aws:bedrock:${data.aws_region.current.region}::foundation-model/${local.titan_text_embeddings_v2_model_id}"
  )

  knowledge_source_object_arn = (
    "${aws_s3_bucket.data.arn}/${local.knowledge_publication_prefix}/*"
  )
}

resource "aws_s3vectors_vector_bucket" "knowledge" {
  vector_bucket_name = local.knowledge_vector_bucket_name
  force_destroy      = false

  encryption_configuration {
    sse_type = "AES256"
  }

  tags = {
    Purpose = "knowledge-retrieval-vectors"
  }
}

resource "aws_s3vectors_index" "knowledge" {
  index_name         = local.knowledge_vector_index_name
  vector_bucket_name = aws_s3vectors_vector_bucket.knowledge.vector_bucket_name

  data_type       = "float32"
  dimension       = 1024
  distance_metric = "cosine"

  encryption_configuration {
    sse_type = "AES256"
  }

  metadata_configuration {
    non_filterable_metadata_keys = [
      "AMAZON_BEDROCK_METADATA",
      "AMAZON_BEDROCK_TEXT",
    ]
  }

  tags = {
    Purpose = "knowledge-retrieval-v1"
  }
}

data "aws_iam_policy_document" "knowledge_base_assume_role" {
  statement {
    sid     = "AllowBedrockKnowledgeBaseService"
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["bedrock.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }

    condition {
      test     = "ArnLike"
      variable = "AWS:SourceArn"
      values = [
        "arn:aws:bedrock:${data.aws_region.current.region}:${data.aws_caller_identity.current.account_id}:knowledge-base/*",
      ]
    }
  }
}

resource "aws_iam_role" "knowledge_base" {
  name        = local.knowledge_base_role_name
  description = "Service role for the bounded OpsLens Bedrock Knowledge Base."

  assume_role_policy = data.aws_iam_policy_document.knowledge_base_assume_role.json

  tags = {
    Purpose = "bedrock-knowledge-base-runtime"
  }
}

data "aws_iam_policy_document" "knowledge_base" {
  statement {
    sid    = "InvokeExactEmbeddingModel"
    effect = "Allow"

    actions = [
      "bedrock:InvokeModel",
    ]

    resources = [
      local.titan_text_embeddings_v2_model_arn,
    ]
  }

  statement {
    sid    = "ListKnowledgeCorpusPrefix"
    effect = "Allow"

    actions = [
      "s3:ListBucket",
    ]

    resources = [
      aws_s3_bucket.data.arn,
    ]

    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values = [
        local.knowledge_publication_prefix,
        "${local.knowledge_publication_prefix}/*",
      ]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:ResourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }
  }

  statement {
    sid    = "ReadKnowledgeCorpusObjects"
    effect = "Allow"

    actions = [
      "s3:GetObject",
    ]

    resources = [
      local.knowledge_source_object_arn,
    ]

    condition {
      test     = "StringEquals"
      variable = "aws:ResourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }
  }

  statement {
    sid    = "UseExactKnowledgeVectorIndex"
    effect = "Allow"

    actions = [
      "s3vectors:DeleteVectors",
      "s3vectors:GetIndex",
      "s3vectors:GetVectors",
      "s3vectors:PutVectors",
      "s3vectors:QueryVectors",
    ]

    resources = [
      aws_s3vectors_index.knowledge.index_arn,
    ]
  }
}

resource "aws_iam_role_policy" "knowledge_base" {
  name = "OpsLensDevBedrockKnowledgeBaseAccess"
  role = aws_iam_role.knowledge_base.id

  policy = data.aws_iam_policy_document.knowledge_base.json
}

resource "aws_bedrockagent_knowledge_base" "knowledge" {
  name        = local.knowledge_base_name
  description = "OpsLens v1 explanatory and remediation knowledge corpus."
  role_arn    = aws_iam_role.knowledge_base.arn

  knowledge_base_configuration {
    type = "VECTOR"

    vector_knowledge_base_configuration {
      embedding_model_arn = local.titan_text_embeddings_v2_model_arn

      embedding_model_configuration {
        bedrock_embedding_model_configuration {
          dimensions          = 1024
          embedding_data_type = "FLOAT32"
        }
      }
    }
  }

  storage_configuration {
    type = "S3_VECTORS"

    s3_vectors_configuration {
      index_arn = aws_s3vectors_index.knowledge.index_arn
    }
  }

  depends_on = [
    aws_iam_role_policy.knowledge_base,
  ]

  tags = {
    Purpose = "knowledge-retrieval-v1"
  }
}

resource "aws_bedrockagent_data_source" "knowledge" {
  knowledge_base_id    = aws_bedrockagent_knowledge_base.knowledge.id
  name                 = local.knowledge_data_source_name
  description          = "Nine pre-split canonical OpsLens remediation/documentation chunks."
  data_deletion_policy = "DELETE"

  data_source_configuration {
    type = "S3"

    s3_configuration {
      bucket_arn              = aws_s3_bucket.data.arn
      bucket_owner_account_id = data.aws_caller_identity.current.account_id
      inclusion_prefixes = [
        "${local.knowledge_publication_prefix}/",
      ]
    }
  }

  vector_ingestion_configuration {
    chunking_configuration {
      chunking_strategy = "NONE"
    }
  }
}

output "knowledge_vector_bucket_arn" {
  description = "ARN of the S3 Vectors bucket used by the Phase 7 knowledge base."
  value       = aws_s3vectors_vector_bucket.knowledge.vector_bucket_arn
}

output "knowledge_vector_index_arn" {
  description = "ARN of the S3 Vectors index used by the Phase 7 knowledge base."
  value       = aws_s3vectors_index.knowledge.index_arn
}

output "knowledge_base_id" {
  description = "ID of the Phase 7 Bedrock Knowledge Base."
  value       = aws_bedrockagent_knowledge_base.knowledge.id
}

output "knowledge_base_arn" {
  description = "ARN of the Phase 7 Bedrock Knowledge Base."
  value       = aws_bedrockagent_knowledge_base.knowledge.arn
}

output "knowledge_data_source_id" {
  description = "ID of the S3 data source attached to the Phase 7 knowledge base."
  value       = aws_bedrockagent_data_source.knowledge.data_source_id
}

output "knowledge_base_service_role_arn" {
  description = "ARN of the dedicated Bedrock Knowledge Base service role."
  value       = aws_iam_role.knowledge_base.arn
}

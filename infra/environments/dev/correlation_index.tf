# The derived correlation index the public request path reads (ADR 0087, ADR 0088).
#
# Two tables rather than one: GHSA is keyed by package and carries a sort key, NVD is
# keyed by CVE and does not. Collapsing them into one table would mean an encoding that
# distinguishes the two entity kinds, and the key encoding is exactly where a silent
# mismatch turns an advisory into a package that no longer matches.
#
# Both partition keys carry the build generation as a prefix, so a rebuild writes into a
# key space nothing is reading and a pointer makes it live. Rows of retired generations
# leave by TTL rather than by a delete the build has to get right.
#
#     partially built index != index
#     written != readable
#
# The manifest and the pointer are not here. They are content-addressed evidence and a
# single small object, so they live in the versioned data bucket with every other
# manifest in this repository — which also means the bucket's own versioning retains
# each pointer value, making "which index answered on a given day" recoverable rather
# than lost to the next swap.

locals {
  correlation_index_ghsa_table_name = "opslens-dev-correlation-index-ghsa"
  correlation_index_nvd_table_name  = "opslens-dev-correlation-index-nvd"
}

resource "aws_dynamodb_table" "correlation_index_ghsa" {
  # checkov:skip=CKV_AWS_28: Point-in-time recovery restores data that cannot be
  # reconstructed. Every row here is derived from Silver by a scheduled projection, so
  # recovery is a rebuild, and a restored index would be a stale one presented as
  # current.
  # checkov:skip=CKV_AWS_119: A customer-managed key is not justified for a projection
  # of public advisory data that carries nothing the sources do not publish.

  name         = local.correlation_index_ghsa_table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"
  range_key    = "sk"

  deletion_protection_enabled = true

  attribute {
    name = "pk"
    type = "S"
  }

  attribute {
    name = "sk"
    type = "S"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = {
    Purpose = "correlation-index-ghsa-by-package"
    Gate    = "20.1"
  }
}

resource "aws_dynamodb_table" "correlation_index_nvd" {
  # checkov:skip=CKV_AWS_28: Derived from Silver by a scheduled projection; recovery is
  # a rebuild, and a restored index would be a stale one presented as current.
  # checkov:skip=CKV_AWS_119: A customer-managed key is not justified for a projection
  # of public advisory data that carries nothing the sources do not publish.

  name         = local.correlation_index_nvd_table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"

  deletion_protection_enabled = true

  attribute {
    name = "pk"
    type = "S"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = {
    Purpose = "correlation-index-nvd-by-cve"
    Gate    = "20.1"
  }
}

output "correlation_index_ghsa_table_name" {
  description = "Name of the GHSA-by-package correlation index table."
  value       = aws_dynamodb_table.correlation_index_ghsa.name
}

output "correlation_index_nvd_table_name" {
  description = "Name of the NVD-by-CVE correlation index table."
  value       = aws_dynamodb_table.correlation_index_nvd.name
}

resource "aws_glue_catalog_database" "opslens" {
  catalog_id = data.aws_caller_identity.current.account_id
  name       = "opslens_dev"

  description = "OpsLens development analytics catalog."
}

resource "aws_glue_catalog_table" "epss_scores" {
  catalog_id    = data.aws_caller_identity.current.account_id
  database_name = aws_glue_catalog_database.opslens.name
  name          = "epss_scores"

  description = "Daily FIRST EPSS Silver snapshots stored as Parquet."

  table_type = "EXTERNAL_TABLE"

  parameters = {
    EXTERNAL                        = "TRUE"
    classification                  = "parquet"
    "parquet.compression"           = "SNAPPY"
    "projection.enabled"            = "true"
    "projection.snapshot_date.type" = "injected"

    "storage.location.template" = (
      "s3://${aws_s3_bucket.data.id}/silver/epss/snapshot_date=$${snapshot_date}/"
    )
  }

  partition_keys {
    name = "snapshot_date"
    type = "string"
  }

  storage_descriptor {
    location = "s3://${aws_s3_bucket.data.id}/silver/epss/"

    compressed = true

    input_format = (
      "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    )

    output_format = (
      "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"
    )

    columns {
      name = "cve"
      type = "string"
    }

    columns {
      name = "epss"
      type = "double"
    }

    columns {
      name = "percentile"
      type = "double"
    }

    columns {
      name = "model_version"
      type = "string"
    }

    columns {
      name = "score_timestamp"
      type = "timestamp"
    }

    columns {
      name = "source"
      type = "string"
    }

    columns {
      name = "source_sha256"
      type = "string"
    }

    ser_de_info {
      name = "ParquetHiveSerDe"

      serialization_library = (
        "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
      )
    }
  }
}

resource "aws_glue_catalog_table" "kev_entries" {
  catalog_id    = data.aws_caller_identity.current.account_id
  database_name = aws_glue_catalog_database.opslens.name
  name          = "kev_entries"

  description = "Daily CISA KEV Silver snapshots stored as deterministic Parquet evidence."

  table_type = "EXTERNAL_TABLE"

  parameters = {
    EXTERNAL                        = "TRUE"
    classification                  = "parquet"
    "parquet.compression"           = "SNAPPY"
    "projection.enabled"            = "true"
    "projection.snapshot_date.type" = "injected"

    "storage.location.template" = (
      "s3://${aws_s3_bucket.data.id}/silver/kev/snapshot_date=$${snapshot_date}/"
    )
  }

  partition_keys {
    name = "snapshot_date"
    type = "string"
  }

  storage_descriptor {
    location = "s3://${aws_s3_bucket.data.id}/silver/kev/"

    compressed = true

    input_format = (
      "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    )

    output_format = (
      "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"
    )

    columns {
      name = "cve"
      type = "string"
    }

    columns {
      name = "vendor_project"
      type = "string"
    }

    columns {
      name = "product"
      type = "string"
    }

    columns {
      name = "vulnerability_name"
      type = "string"
    }

    columns {
      name = "date_added"
      type = "date"
    }

    columns {
      name = "short_description"
      type = "string"
    }

    columns {
      name = "required_action"
      type = "string"
    }

    columns {
      name = "due_date"
      type = "date"
    }

    columns {
      name = "known_ransomware_campaign_use"
      type = "string"
    }

    columns {
      name = "notes"
      type = "string"
    }

    columns {
      name = "cwes"
      type = "array<string>"
    }

    columns {
      name = "catalog_version"
      type = "string"
    }

    columns {
      name = "catalog_date_released"
      type = "timestamp"
    }

    columns {
      name = "source"
      type = "string"
    }

    columns {
      name = "source_sha256"
      type = "string"
    }

    columns {
      name = "retrieved_at"
      type = "timestamp"
    }

    ser_de_info {
      name = "ParquetHiveSerDe"

      serialization_library = (
        "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
      )
    }
  }
}

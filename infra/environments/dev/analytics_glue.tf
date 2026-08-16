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

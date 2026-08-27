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

resource "aws_glue_catalog_table" "nvd_cve_versions" {
  catalog_id    = data.aws_caller_identity.current.account_id
  database_name = aws_glue_catalog_database.opslens.name
  name          = "nvd_cve_versions"

  description = "Permanent exact-authority NVD CVE analytics projections stored as clean Parquet."

  table_type = "EXTERNAL_TABLE"

  parameters = {
    EXTERNAL                                   = "TRUE"
    classification                             = "parquet"
    "parquet.compression"                      = "SNAPPY"
    "projection.enabled"                       = "true"
    "projection.source_kind_partition.type"    = "enum"
    "projection.source_kind_partition.values"  = "bootstrap,incremental"
    "projection.projection_date.type"          = "date"
    "projection.projection_date.range"         = "2026-01-01,NOW"
    "projection.projection_date.format"        = "yyyy-MM-dd"
    "projection.projection_date.interval"      = "1"
    "projection.projection_date.interval.unit" = "DAYS"

    "storage.location.template" = (
      "s3://${aws_s3_bucket.data.id}/analytics/nvd/cve/schema_version=1/source_kind=$${source_kind_partition}/projection_date=$${projection_date}/"
    )
  }

  partition_keys {
    name = "source_kind_partition"
    type = "string"
  }

  partition_keys {
    name = "projection_date"
    type = "string"
  }

  storage_descriptor {
    location = (
      "s3://${aws_s3_bucket.data.id}/analytics/nvd/cve/schema_version=1/"
    )

    compressed = true

    input_format = (
      "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    )

    output_format = (
      "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"
    )

    columns {
      name = "schema_version"
      type = "smallint"
    }

    columns {
      name = "cve_id"
      type = "string"
    }

    columns {
      name = "observed_cve_version_id"
      type = "string"
    }

    columns {
      name = "source_cve_sha256"
      type = "string"
    }

    columns {
      name = "observation_id"
      type = "string"
    }

    columns {
      name = "source_kind"
      type = "string"
    }

    columns {
      name = "source_batch_id"
      type = "string"
    }

    columns {
      name = "source_observed_at"
      type = "timestamp"
    }

    columns {
      name = "bronze_manifest_key"
      type = "string"
    }

    columns {
      name = "bronze_manifest_version_id"
      type = "string"
    }

    columns {
      name = "bronze_manifest_sha256"
      type = "string"
    }

    columns {
      name = "bronze_object_key"
      type = "string"
    }

    columns {
      name = "bronze_object_version_id"
      type = "string"
    }

    columns {
      name = "bronze_object_sha256"
      type = "string"
    }

    columns {
      name = "bronze_record_index"
      type = "bigint"
    }

    columns {
      name = "bootstrap_feed_year"
      type = "smallint"
    }

    columns {
      name = "bootstrap_feed_revision"
      type = "string"
    }

    columns {
      name = "incremental_update_id"
      type = "string"
    }

    columns {
      name = "incremental_page_start"
      type = "bigint"
    }

    columns {
      name = "source_identifier"
      type = "string"
    }

    columns {
      name = "published_at"
      type = "timestamp"
    }

    columns {
      name = "last_modified_at"
      type = "timestamp"
    }

    columns {
      name = "vuln_status"
      type = "string"
    }

    columns {
      name = "is_rejected"
      type = "boolean"
    }

    columns {
      name = "descriptions"
      type = "array<struct<lang:string,value:string>>"
    }

    columns {
      name = "cve_tags"
      type = "array<struct<source_identifier:string,tags:array<string>>>"
    }

    columns {
      name = "weaknesses"
      type = "array<struct<source:string,type:string,descriptions:array<struct<lang:string,value:string>>>>"
    }

    columns {
      name = "cwe_ids"
      type = "array<string>"
    }

    columns {
      name = "references"
      type = "array<struct<url:string,source:string,tags:array<string>>>"
    }

    columns {
      name = "cvss_metrics"
      type = "array<struct<family:string,version:string,source:string,type:string,vector_string:string,base_score:double,base_severity:string,exploitability_score:double,impact_score:double,metric_json:string>>"
    }

    columns {
      name = "configurations_json"
      type = "string"
    }

    columns {
      name = "configuration_count"
      type = "int"
    }

    ser_de_info {
      name = "ParquetHiveSerDe"

      serialization_library = (
        "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
      )
    }
  }
}

resource "aws_glue_catalog_table" "ghsa_advisory_versions" {
  catalog_id    = data.aws_caller_identity.current.account_id
  database_name = aws_glue_catalog_database.opslens.name
  name          = "ghsa_advisory_versions"

  description = "Authoritative GHSA advisory content versions stored as deterministic one-row Parquet evidence."

  table_type = "EXTERNAL_TABLE"

  parameters = {
    EXTERNAL              = "TRUE"
    classification        = "parquet"
    "parquet.compression" = "SNAPPY"
  }

  storage_descriptor {
    location = (
      "s3://${aws_s3_bucket.data.id}/silver/ghsa/advisory_versions/schema_version=1/"
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
      name = "ghsa_id"
      type = "string"
    }

    columns {
      name = "observed_advisory_version_id"
      type = "string"
    }

    columns {
      name = "source_advisory_sha256"
      type = "string"
    }

    columns {
      name = "cve_id"
      type = "string"
    }

    columns {
      name = "advisory_type"
      type = "string"
    }

    columns {
      name = "severity"
      type = "string"
    }

    columns {
      name = "url"
      type = "string"
    }

    columns {
      name = "html_url"
      type = "string"
    }

    columns {
      name = "repository_advisory_url"
      type = "string"
    }

    columns {
      name = "source_code_location"
      type = "string"
    }

    columns {
      name = "summary"
      type = "string"
    }

    columns {
      name = "description"
      type = "string"
    }

    columns {
      name = "published_at"
      type = "timestamp"
    }

    columns {
      name = "updated_at"
      type = "timestamp"
    }

    columns {
      name = "github_reviewed_at"
      type = "timestamp"
    }

    columns {
      name = "nvd_published_at"
      type = "timestamp"
    }

    columns {
      name = "withdrawn_at"
      type = "timestamp"
    }

    columns {
      name = "is_withdrawn"
      type = "boolean"
    }

    columns {
      name = "identifiers"
      type = "array<struct<type:string,value:string>>"
    }

    columns {
      name = "references"
      type = "array<string>"
    }

    columns {
      name = "cwes"
      type = "array<struct<cwe_id:string,name:string>>"
    }

    columns {
      name = "cvss_metrics"
      type = "array<struct<family:string,vector_string:string,score:double>>"
    }

    columns {
      name = "cvss_severities_json"
      type = "string"
    }

    columns {
      name = "vulnerability_entry_count"
      type = "int"
    }

    columns {
      name = "vulnerabilities"
      type = "array<struct<source_index:int,vulnerability_entry_id:string,source_entry_sha256:string,ecosystem:string,package_name:string,vulnerable_version_range:string,first_patched_version:string,vulnerable_functions:array<string>,source_entry_json:string>>"
    }

    ser_de_info {
      name = "ParquetHiveSerDe"

      serialization_library = (
        "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
      )
    }
  }
}

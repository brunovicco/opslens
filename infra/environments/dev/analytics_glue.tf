resource "aws_glue_catalog_database" "opslens" {
  catalog_id = data.aws_caller_identity.current.account_id
  name       = "opslens_dev"

  description = "OpsLens development analytics catalog."
}

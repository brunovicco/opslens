resource "aws_iam_service_linked_role" "bedrock_agentcore_runtime_identity" {
  aws_service_name = "runtime-identity.bedrock-agentcore.amazonaws.com"
  description      = "Service-linked role required by Amazon Bedrock AgentCore Runtime identity."

  lifecycle {
    prevent_destroy = true
  }
}

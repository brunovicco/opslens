# Gate 19.7 partial-apply recovery override.
#
# The historical Gate 19.4 contract configured API reserved concurrency at 2.
# The first Gate 19.7 apply proved that the dev account concurrency limit of 10
# cannot admit any positive reservation while AWS preserves its minimum
# unreserved concurrency. Recovery therefore tightens the disabled boundary:
# both API and worker Lambdas remain at reserved concurrency 0 until a later,
# separately authorized runtime-enablement gate.
#
# Terraform override semantics intentionally leave the historical Gate 19.4
# source/evidence unchanged while replacing only this current materialization
# attribute for the Gate 19.7 recovery plan.
resource "aws_lambda_function" "public_async_api" {
  reserved_concurrent_executions = 0
}

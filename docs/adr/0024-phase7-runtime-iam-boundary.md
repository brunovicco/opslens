# ADR 0024 — Phase 7 Future Application Runtime IAM Boundary

- **Status:** Accepted
- **Date:** 2026-09-06
- **Phase:** 7 — Knowledge Retrieval with Bedrock
- **Decision scope:** future deployed application runtime identity only

## Context

Phase 7 proved a bounded runtime path with two AWS data-plane operations:

```text
Bedrock Knowledge Base Retrieve
 -> deterministic evidence admission
 -> deterministic context/citation authority
 -> non-streaming Bedrock Converse synthesis
```

The real laboratory runs were executed by a temporary human IAM Identity Center session. OpsLens still has no deployed application compute principal.

Creating a runtime role before compute exists would create a dead identity and would blur the existing responsibility split between:

```text
human operator
GitHub Actions deployment identity
Bedrock Knowledge Base service role
future application runtime identity
```

Gate 7.8 therefore freezes the minimum future entitlement without instantiating it.

Current official AWS documentation checked on 2026-09-06 establishes two relevant authorization behaviors:

1. `Retrieve` can be authorized with `bedrock:Retrieve` scoped to a specific Knowledge Base ARN.
2. Non-streaming `Converse` uses the `bedrock:InvokeModel` IAM action. When a Geographic cross-Region inference profile is used, authorization is evaluated for the inference-profile resource and for the foundation model in the source and each candidate destination Region. Foundation-model permissions can be restricted with the `bedrock:InferenceProfileArn` condition key.

The selected Phase 7 synthesis profile is:

```text
us.anthropic.claude-haiku-4-5-20251001-v1:0
```

For source Region `us-east-1`, AWS currently documents these destination Regions for Claude Haiku 4.5 US Geographic inference:

```text
us-east-1
us-east-2
us-west-2
```

## Decision

Do not create an application runtime role in Phase 7.

When a real deployed application compute principal is introduced, its initial Bedrock entitlement must be derived from the already-proven runtime path and remain narrower than human/deployment/service-role permissions.

### Retrieval permission

Allow only direct Knowledge Base retrieval against the exact OpsLens Knowledge Base:

```json
{
  "Sid": "RetrieveOpsLensKnowledgeBase",
  "Effect": "Allow",
  "Action": "bedrock:Retrieve",
  "Resource": "arn:aws:bedrock:us-east-1:487757851499:knowledge-base/BTVJ2PBR2A"
}
```

The application runtime does not need `bedrock:GetKnowledgeBase` merely to call a configured, already-known Knowledge Base ID. Add that action later only if a concrete runtime requirement appears.

### Non-streaming synthesis permission

Allow `bedrock:InvokeModel` for the exact Geographic inference profile:

```json
{
  "Sid": "InvokeExactOpsLensInferenceProfile",
  "Effect": "Allow",
  "Action": "bedrock:InvokeModel",
  "Resource": "arn:aws:bedrock:us-east-1:487757851499:inference-profile/us.anthropic.claude-haiku-4-5-20251001-v1:0"
}
```

Allow the same action on the exact foundation-model resources that the US Geographic profile can use from `us-east-1`, conditioned on the exact profile ARN:

```json
{
  "Sid": "InvokeExactOpsLensGeoDestinationModels",
  "Effect": "Allow",
  "Action": "bedrock:InvokeModel",
  "Resource": [
    "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-haiku-4-5-20251001-v1:0",
    "arn:aws:bedrock:us-east-2::foundation-model/anthropic.claude-haiku-4-5-20251001-v1:0",
    "arn:aws:bedrock:us-west-2::foundation-model/anthropic.claude-haiku-4-5-20251001-v1:0"
  ],
  "Condition": {
    "StringEquals": {
      "bedrock:InferenceProfileArn": "arn:aws:bedrock:us-east-1:487757851499:inference-profile/us.anthropic.claude-haiku-4-5-20251001-v1:0"
    }
  }
}
```

The two synthesis statements are both required by the Geographic cross-Region authorization model: access to the profile alone is not sufficient.

### Explicitly excluded permissions

The Phase 7 proven runtime does not justify:

```text
bedrock:RetrieveAndGenerate
bedrock:InvokeModelWithResponseStream
bedrock:ConverseStream as a separate streaming entitlement
bedrock:GetKnowledgeBase
bedrock:ListKnowledgeBases
Knowledge Base create/update/delete actions
data-source management actions
ingestion-job management actions
S3 Vectors direct runtime access
S3 direct corpus-object reads by the application
broad bedrock:* administration
```

`Converse` itself is not a separate IAM action; the runtime authorization is `bedrock:InvokeModel`.

Streaming remains excluded because Phase 7 deliberately uses non-streaming Converse and validates one complete bounded assistant response.

## Service-role separation

The Bedrock Knowledge Base service role remains separate and retains only the permissions required for Knowledge Base ingestion/vector-store integration.

The future application runtime must not assume that service role and does not receive the service role's storage/embedding integration permissions.

```text
application runtime
 -> Retrieve + model invocation only

Knowledge Base service role
 -> ingestion/vector integration only
```

This preserves least privilege and makes failures attributable to the correct trust boundary.

## Cross-Region and SCP consequence

Geographic cross-Region inference evaluates candidate destination Regions. Organization SCPs or Region-deny policies must not block a destination required by the selected profile unless a correctly scoped `bedrock:InferenceProfileArn` exception is designed.

An IAM policy that grants only `us-east-1` foundation-model access can still fail at runtime because Bedrock may route the request to `us-east-2` or `us-west-2`.

This is why the destination-model resources are explicit rather than replaced by an account-wide wildcard.

## Observability permissions

This ADR does not pre-authorize CloudWatch write permissions for a runtime that does not yet exist.

When compute is introduced, application telemetry permissions must be designed against the actual logging/metrics/tracing implementation. They should not be hidden inside the Bedrock data-plane policy.

## Alternatives considered

### Reuse the human bootstrap/admin session

Rejected for deployed runtime. Human administration and application execution are different trust boundaries.

### Reuse the Knowledge Base service role

Rejected. The service role exists for Bedrock integration with embeddings/vector storage, not application calls.

### `bedrock:*` on `*`

Rejected. It grants control-plane and unrelated model capabilities that the proven path does not require.

### Grant only the inference-profile ARN

Rejected. Geographic cross-Region inference also authorizes the underlying foundation-model resources in source/destination Regions.

### Grant `InvokeModelWithResponseStream`

Rejected for Phase 7. The implemented contract is intentionally non-streaming.

### Create the role now

Rejected. There is no deployed compute principal to assume it, so doing so would introduce unused infrastructure and premature trust configuration.

## Consequences

Positive:

- future runtime starts from a reviewed least-privilege policy shape;
- retrieval and generation permissions remain independently revocable;
- Knowledge Base administration is excluded from application runtime;
- geographic routing requirements are explicit rather than discovered through production AccessDenied errors;
- no dead IAM principal is created during the laboratory phase.

Trade-offs:

- model/profile or destination-Region changes require explicit IAM review;
- SCP changes can affect Geographic inference even when identity policy is unchanged;
- the documented policy must be revalidated against current AWS documentation before actual deployment because model/profile availability can change.

## Validation requirement before deployment

Before attaching this policy to any real compute principal:

```text
1. re-check current official Bedrock IAM documentation
2. re-check the exact inference profile source/destination Regions
3. verify the model/profile remains active
4. inspect Organization SCP / Region restrictions
5. deploy the role only with the real compute trust policy
6. run one positive Retrieve test
7. run one negative RetrieveAndGenerate authorization test
8. run one positive non-streaming Converse test
9. run one negative streaming authorization test
10. capture request IDs, IAM failure evidence, latency, retries, and cost evidence
```

## References checked on 2026-09-06

- https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-prereq-permissions-general.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/geographic-cross-region-inference.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-haiku-4-5.html
- https://docs.aws.amazon.com/bedrock/latest/userguide/inference.html

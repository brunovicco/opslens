# Phase 2.5D-3 — Terraform apply workflow artifact fix

Status: VALIDATED — READY FOR MERGE

## Failure observed

GitHub Actions run `33346900957` (job `99352623205`) failed during `terraform validate` before Terraform plan/apply.

The failure was deterministic and unrelated to the historical EPSS runtime itself:

```text
nvd_incremental_lambda.tf line 33
filebase64sha256("../../../dist/opslens-nvd-incremental.zip")
no such file or directory
```

The historical transformer package built successfully and its content-addressed artifact was published create-only before validation:

```text
sha256=01a85fb532b4df4a7eed799ce0d575e91ad246f3eee5572af070bab3e96094ec
size_bytes=67387627
version_id=O1lKk3wm_NH6B_mdd4gvHTngrel7jSY8
```

No Terraform plan or apply ran. No historical Bronze, Silver, or completion objects were created.

## Fix

`terraform-dev-apply.yml` now builds the two Terraform-required NVD artifacts that were already proven necessary by the Phase 2.5D-2 validation workflow:

```text
scripts/build_nvd_incremental_lambda_package.py
scripts/build_nvd_analytics_projector_lambda_package.py
```

This is intentionally limited to the deploy workflow. No Terraform resources, runtime code, IAM policies, or historical execution controls were changed.

## Validation

Temporary validation workflow:

```text
workflow  Validate EPSS History D3 Apply Fix
run       33347300694
job       99353763464
commit    62b28ce76d2fb2a25a437a18c8f551d816be86f5
result    SUCCESS
```

Validated:

```text
all Terraform-required Lambda package builds
terraform init -backend=false
terraform validate
apply workflow contains both missing NVD builders
EPSS_HISTORY_D3_APPLY_ARTIFACT_FIX_GATE=PASS
```

The temporary validation workflow is removed after this proof so it does not remain as permanent repository surface.

## Next gate

After merge to `main`, rerun `Terraform Dev Apply` and stop for review after deployment. Do not execute the EPSS historical canary until the apply is verified.

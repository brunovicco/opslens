# Scheduled Ingestion Pause Runbook

## Purpose

Pause and resume only the three Terraform-managed recurring source-ingestion schedules in the OpsLens dev environment.

This runbook is an operational recovery procedure, not a global platform kill switch.

The bounded control is:

```text
scheduled_ingestion_enabled=true   -> recurring schedules ENABLED
scheduled_ingestion_enabled=false  -> recurring schedules DISABLED
```

Affected resources:

```text
aws_scheduler_schedule.epss_daily
aws_scheduler_schedule.kev_daily
aws_scheduler_schedule.nvd_incremental_hourly
```

Deployed Scheduler coordinates:

```text
EPSS  group=opslens-dev-epss             name=opslens-dev-epss-daily
KEV   group=opslens-dev-kev              name=opslens-dev-kev-daily
NVD   group=opslens-dev-nvd-incremental  name=opslens-dev-nvd-incremental-hourly
```

## What a pause does not do

Setting `scheduled_ingestion_enabled=false` does not cancel or revoke:

```text
in-flight Lambda invocations
Scheduler deliveries already accepted for retry
S3 notifications already emitted or being processed
manual Lambda invocations
historical/manual workflows
model invocations through separate paths
capability authorization
```

The downstream S3 event chain remains enabled so already-admitted work can complete or reach its existing failure destination.

## Safety rule

While a pause is active, every Terraform `plan` or `apply` for `infra/environments/dev` must explicitly include:

```text
-var='scheduled_ingestion_enabled=false'
```

The Terraform default is intentionally `true`. Therefore, an ordinary plan/apply that omits the explicit `false` value is a **resume request**, not an inert operation.

## Prerequisites

Use the protected `main` commit containing ADR 0069 and the Gate 17.6 implementation. Do not run the live pause experiment from an unmerged branch.

```bash
cd ~/Projects/opslens

git switch main
git pull

git status --short

aws sso login --profile opslens-bootstrap

AWS_PROFILE=opslens-bootstrap \
terraform -chdir=infra/environments/dev init \
  -reconfigure \
  -input=false
```

`git status --short` must be empty before continuing.

## 1. Prove normal-state convergence

Before changing operational state, prove the normal desired configuration is already converged:

```bash
set +e
AWS_PROFILE=opslens-bootstrap \
terraform -chdir=infra/environments/dev plan \
  -input=false \
  -lock-timeout=30s \
  -detailed-exitcode
rc=$?
set -e

echo "terraform_default_plan_exit_code=$rc"
```

Expected:

```text
No changes. Your infrastructure matches the configuration.
terraform_default_plan_exit_code=0
```

Any resource change at this point is unrelated drift. Stop and investigate before attempting the pause.

## 2. Produce the bounded pause plan

```bash
AWS_PROFILE=opslens-bootstrap \
terraform -chdir=infra/environments/dev plan \
  -input=false \
  -lock-timeout=30s \
  -var='scheduled_ingestion_enabled=false' \
  -out=/tmp/opslens-gate17-6-pause.tfplan

terraform -chdir=infra/environments/dev show \
  -no-color \
  /tmp/opslens-gate17-6-pause.tfplan \
  | tee /tmp/opslens-gate17-6-pause-plan.txt
```

The resource summary must be exactly:

```text
Plan: 0 to add, 3 to change, 0 to destroy.
```

The only resource changes permitted are:

```text
aws_scheduler_schedule.epss_daily
aws_scheduler_schedule.kev_daily
aws_scheduler_schedule.nvd_incremental_hourly
```

For each resource, the only intended operational state transition is:

```text
state = "ENABLED" -> "DISABLED"
```

No Lambda, S3 notification, IAM, queue, schedule group, target ARN, cron expression, input payload, retry budget, or other resource may change.

If the plan contains any additional change, **STOP / DO NOT APPLY**.

## 3. Apply only the inspected pause plan

```bash
AWS_PROFILE=opslens-bootstrap \
terraform -chdir=infra/environments/dev apply \
  -input=false \
  -lock-timeout=30s \
  /tmp/opslens-gate17-6-pause.tfplan
```

Expected resource summary:

```text
Apply complete! Resources: 0 added, 3 changed, 0 destroyed.
```

## 4. Independently verify all schedules are disabled

```bash
aws scheduler get-schedule \
  --group-name opslens-dev-epss \
  --name opslens-dev-epss-daily \
  --profile opslens-bootstrap \
  --region us-east-1 \
  --query '{Name:Name,State:State}' \
  --output json

aws scheduler get-schedule \
  --group-name opslens-dev-kev \
  --name opslens-dev-kev-daily \
  --profile opslens-bootstrap \
  --region us-east-1 \
  --query '{Name:Name,State:State}' \
  --output json

aws scheduler get-schedule \
  --group-name opslens-dev-nvd-incremental \
  --name opslens-dev-nvd-incremental-hourly \
  --profile opslens-bootstrap \
  --region us-east-1 \
  --query '{Name:Name,State:State}' \
  --output json
```

All three must report:

```text
"State": "DISABLED"
```

Do not infer that in-flight or downstream already-admitted work has stopped merely because these control-plane states are disabled.

## 5. Keep Terraform aligned while paused

For any dev Terraform inspection during the pause, preserve the explicit value:

```bash
AWS_PROFILE=opslens-bootstrap \
terraform -chdir=infra/environments/dev plan \
  -input=false \
  -lock-timeout=30s \
  -var='scheduled_ingestion_enabled=false'
```

Expected after the pause apply:

```text
No changes. Your infrastructure matches the configuration.
```

A plan without the explicit `false` value should propose the three schedule state changes back to `ENABLED`; that is the designed resume path.

## 6. Produce the bounded resume plan

When normal recurring ingestion should resume:

```bash
AWS_PROFILE=opslens-bootstrap \
terraform -chdir=infra/environments/dev plan \
  -input=false \
  -lock-timeout=30s \
  -var='scheduled_ingestion_enabled=true' \
  -out=/tmp/opslens-gate17-6-resume.tfplan

terraform -chdir=infra/environments/dev show \
  -no-color \
  /tmp/opslens-gate17-6-resume.tfplan \
  | tee /tmp/opslens-gate17-6-resume-plan.txt
```

The resource summary must again be exactly:

```text
Plan: 0 to add, 3 to change, 0 to destroy.
```

The same three Scheduler resources must be the only changes, with state transition:

```text
state = "DISABLED" -> "ENABLED"
```

Anything else means **STOP / DO NOT APPLY**.

## 7. Apply only the inspected resume plan

```bash
AWS_PROFILE=opslens-bootstrap \
terraform -chdir=infra/environments/dev apply \
  -input=false \
  -lock-timeout=30s \
  /tmp/opslens-gate17-6-resume.tfplan
```

Expected:

```text
Apply complete! Resources: 0 added, 3 changed, 0 destroyed.
```

## 8. Verify all schedules are enabled again

Repeat the three `aws scheduler get-schedule` commands from step 4.

All three must report:

```text
"State": "ENABLED"
```

## 9. Prove final default convergence

```bash
set +e
AWS_PROFILE=opslens-bootstrap \
terraform -chdir=infra/environments/dev plan \
  -input=false \
  -lock-timeout=30s \
  -detailed-exitcode
rc=$?
set -e

echo "terraform_final_plan_exit_code=$rc"
```

Expected:

```text
No changes. Your infrastructure matches the configuration.
terraform_final_plan_exit_code=0
```

## Evidence to retain

For the first Gate 17.6 measured experiment, preserve only bounded operational evidence:

```text
source main SHA
pause Terraform plan summary and exact changed resource identities
pause apply summary
three independently read DISABLED states
resume Terraform plan summary and exact changed resource identities
resume apply summary
three independently read ENABLED states
final Terraform convergence result / exit code
experiment timestamps
```

Do not copy SSO tokens, AWS credentials, environment dumps, or unrelated provider payloads into repository evidence.

## Interpretation boundaries

```text
scheduler pause != global workload termination
scheduler state != business/evidence authority
recovery control != authorization bypass
pause request != applied AWS state
bounded retry != guaranteed delivery
failure destination != successful recovery
model token budget != tenant quota
no public runtime != proof future edge controls are unnecessary
```

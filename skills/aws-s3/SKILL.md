---
name: aws-s3
description: Handles AWS S3 bucket decisions and operations safely. Use when deciding whether to create a bucket, adopt an existing bucket, manage S3 infrastructure with Terraform, or perform runtime object operations with AWS CLI or SDK. Use when S3 work requires explicit branching between infrastructure management and object operations, with credential checks, region verification, and confirmation gates for destructive deletes.
---

# AWS S3 Skill

> Process-driven guidance for AI agents working with AWS S3. This skill focuses on choosing the correct path first: create vs adopt, Terraform vs CLI/SDK, and safe handling of existing buckets, regions, credentials, and destructive operations.

## Overview

Work with S3 by making the decision in the right order:

1. Verify AWS identity
2. Verify bucket region if the bucket already exists
3. Decide whether the task is infrastructure or runtime object work
4. Decide whether the bucket should be created or adopted
5. Refuse destructive deletes unless the user has explicitly confirmed them

This skill is execution-oriented. It is not a general explainer about AWS. It exists to help an agent act correctly and avoid common S3 mistakes.

## Core Principles

### 1. Verify Identity First

Before any S3 action, confirm the active AWS identity:

```bash
aws sts get-caller-identity
```

If this fails, stop. Do not guess the active account, role, or profile.

### 2. Verify Bucket Region First

Before operating on an existing bucket, verify its region:

```bash
aws s3api get-bucket-location --bucket <bucket_name>
```

If the region is unknown or inconsistent with the configured environment, stop and correct that first.

### 3. Never Recreate an Existing Bucket

If a bucket already exists, do not create a replacement bucket with the same intended purpose. Existing buckets must be adopted, not recreated.

### 4. Keep Infrastructure and Runtime Separate

Use Terraform only for infrastructure:

- Bucket creation
- Bucket versioning
- Bucket encryption
- Managed bucket configuration

Use AWS CLI or SDK only for runtime object operations:

- Listing objects
- Uploading files
- Downloading files
- Syncing folders

Do not use Terraform to upload objects. Do not use AWS CLI or SDK to replace infrastructure management.

### 5. Treat Deletes as Destructive

Any delete operation against S3 objects or buckets is destructive. Require explicit user confirmation before proceeding.

## When to Use

- Creating a new S3 bucket as managed infrastructure
- Bringing an existing S3 bucket under Terraform management
- Operating on objects in an existing bucket
- Determining whether a bucket should be created or adopted
- Determining whether Terraform or AWS CLI/SDK is the correct tool
- Troubleshooting wrong-account, wrong-region, or wrong-bucket mistakes

## When Not to Use

- The task is not about S3
- The request is broad AWS architecture guidance across multiple services
- The task is purely conceptual and no action path needs to be chosen
- The bucket name, account, or intent is too ambiguous to act safely
- A delete is being requested without explicit confirmation

## Decision Flow

### Step 1: Verify AWS Credentials

Run:

```bash
aws sts get-caller-identity
```

If this fails, stop and fix credentials before doing anything else.

### Step 2: Identify the Real Task

Classify the request:

- Infrastructure management
- Runtime object operation

Then determine whether the bucket:

- Already exists
- Needs to be created
- Should be imported into Terraform

### Step 3: Verify Existing Bucket Region

If the bucket already exists, run:

```bash
aws s3api get-bucket-location --bucket <bucket_name>
```

Do this before imports, uploads, downloads, or any other operation.

### Step 4: Choose the Path

- New bucket + infrastructure task: use Workflow 1
- Existing bucket + infrastructure management task: use Workflow 2
- Existing bucket + object operation task: use Workflow 3

### Step 5: Apply Safety Gates

If the requested operation deletes objects or buckets:

- Stop
- Restate the destructive effect clearly
- Require explicit confirmation before proceeding

## Required Inputs

Gather these before acting:

- AWS profile or credential source
- Active AWS identity from `aws sts get-caller-identity`
- Bucket name
- Bucket region for existing buckets
- Whether the bucket already exists
- Whether the task is infrastructure or runtime object work
- Terraform repo or module location, if Terraform is involved
- Explicit confirmation for any delete

## Workflow 1: Create Bucket with Terraform

Use this workflow only when:

- The task is infrastructure provisioning
- No suitable bucket already exists
- The bucket should be managed as infrastructure

### Steps

1. Verify credentials:

```bash
aws sts get-caller-identity
```

2. Confirm the intended bucket does not already exist.
3. If the bucket already exists, do not recreate it. Switch to Workflow 2.
4. Add Terraform configuration for the bucket.
5. Add versioning and encryption if required by the environment.
6. Run `terraform plan`.
7. Review the plan carefully.
8. Apply through the normal Terraform workflow.

### Terraform Bucket Creation Snippet

```hcl
resource "aws_s3_bucket" "bucket" {
  bucket = var.bucket_name

  tags = {
    Name = var.bucket_name
  }
}
```

### Terraform Versioning Snippet

```hcl
resource "aws_s3_bucket_versioning" "bucket" {
  bucket = aws_s3_bucket.bucket.id

  versioning_configuration {
    status = "Enabled"
  }
}
```

### Terraform Encryption Snippet

```hcl
resource "aws_s3_bucket_server_side_encryption_configuration" "bucket" {
  bucket = aws_s3_bucket.bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}
```

### Rules

- Terraform is only for infrastructure
- Do not use AWS CLI to create buckets when the goal is managed infrastructure
- Do not use Terraform for uploads, downloads, or sync operations
- If Terraform indicates the bucket already exists, stop and adopt it instead

## Workflow 2: Adopt Existing Bucket

Use this workflow when:

- The bucket already exists
- The bucket should be managed by Terraform
- Recreating it would be unsafe or incorrect

### Steps

1. Verify credentials:

```bash
aws sts get-caller-identity
```

2. Verify bucket region:

```bash
aws s3api get-bucket-location --bucket <bucket_name>
```

3. Confirm this is the intended bucket for the current environment.
4. Write Terraform that describes the existing bucket.
5. Import it into Terraform state:

```bash
terraform import aws_s3_bucket.bucket <bucket_name>
```

6. Run `terraform plan`.
7. Review drift before applying any changes.

### Rules

- Never recreate an existing bucket to make Terraform state look clean
- Import first, then review the plan
- If the plan shows major unexpected changes, stop and confirm intent
- Make sure provider region matches the real bucket region before import

## Workflow 3: Operate on Bucket

Use this workflow only for runtime object operations. This includes list, upload, download, and sync.

### Pre-Checks

1. Verify credentials:

```bash
aws sts get-caller-identity
```

2. Verify the existing bucket region:

```bash
aws s3api get-bucket-location --bucket <bucket_name>
```

3. Confirm the operation is non-destructive, or that explicit confirmation has been given if destructive.

### Common Commands

List objects:

```bash
aws s3 ls s3://<bucket_name>
```

Upload a file:

```bash
aws s3 cp file.txt s3://<bucket_name>/
```

Download a file:

```bash
aws s3 cp s3://<bucket_name>/file.txt .
```

Sync a folder:

```bash
aws s3 sync ./folder s3://<bucket_name>/
```

### Rules

- AWS CLI or SDK is only for runtime object operations
- Do not use CLI or SDK as a substitute for infrastructure-as-code
- Verify bucket and region before write operations
- Treat delete-capable variants of `sync`, `rm`, or recursive removal as destructive

## Safety Checks

- `aws sts get-caller-identity` succeeds before any action
- Existing bucket region is verified with `aws s3api get-bucket-location --bucket <bucket_name>`
- The task is correctly classified as infrastructure vs runtime
- The bucket is not being recreated if it already exists
- Terraform is only being used for infrastructure
- AWS CLI or SDK is only being used for object operations
- The target bucket and account are unambiguous
- Terraform plan has been reviewed before apply
- Any delete action has explicit confirmation

## Common Failure Cases

| Failure | Cause | Correct Response |
|---|---|---|
| `aws sts get-caller-identity` fails | Missing, expired, or wrong credentials | Stop and fix credentials first |
| Bucket create fails | Bucket name is globally taken or already exists | Do not retry blindly; verify whether it should be adopted or renamed |
| Agent tries to create a bucket that already exists | Wrong create vs adopt decision | Stop and switch to Workflow 2 |
| Upload or download is attempted through Terraform | Wrong tool choice | Use AWS CLI or SDK instead |
| Bucket infrastructure is changed with CLI instead of Terraform | Management boundary broken | Return infrastructure changes to Terraform and review drift |
| S3 commands fail with access or signature errors | Wrong region or wrong account | Re-check identity and bucket location |
| Terraform wants to replace an existing bucket | Import was skipped or config is wrong | Stop, import correctly, and re-plan |
| Delete-capable operation is about to run without confirmation | Safety gate missing | Stop and require explicit confirmation |

## Recovery Steps

### If Credentials Are Wrong

1. Refresh credentials or switch profiles
2. Re-run:

```bash
aws sts get-caller-identity
```

3. Do not continue until identity is confirmed

### If Bucket Region Is Wrong

1. Re-check:

```bash
aws s3api get-bucket-location --bucket <bucket_name>
```

2. Update the CLI profile, environment, or Terraform provider configuration to match
3. Retry only after region alignment is confirmed

### If Terraform Tries to Recreate an Existing Bucket

1. Stop immediately
2. Remove the incorrect assumption that the bucket should be newly created
3. Import the real bucket:

```bash
terraform import aws_s3_bucket.bucket <bucket_name>
```

4. Re-run `terraform plan`

### If Runtime Object Access Fails

1. Verify identity again:

```bash
aws sts get-caller-identity
```

2. Verify region again:

```bash
aws s3api get-bucket-location --bucket <bucket_name>
```

3. Test basic visibility:

```bash
aws s3 ls s3://<bucket_name>
```

4. Retry only after confirming the target bucket is correct

### If a Delete Is Requested Without Confirmation

- Do not execute the delete
- Ask for explicit confirmation
- Restate exactly what will be deleted

## Anti-Patterns

- Creating a new bucket because Terraform state is missing
- Recreating an existing bucket instead of importing it
- Using Terraform for uploads, downloads, or sync operations
- Using AWS CLI or SDK as a substitute for infrastructure management
- Skipping `aws sts get-caller-identity`
- Skipping `aws s3api get-bucket-location --bucket <bucket_name>` for existing buckets
- Applying Terraform changes without reviewing the plan
- Running delete-capable S3 operations without explicit confirmation
- Mixing infrastructure changes and runtime object work into one unstructured workflow

## Example Scenarios

### Scenario 1: New Managed Bucket

The user needs a bucket for a new environment and expects it to be managed as infrastructure.

Use Workflow 1:

- Verify credentials
- Confirm the bucket does not already exist
- Create it with Terraform
- Add versioning and encryption
- Review the plan before apply

### Scenario 2: Existing Bucket Must Be Managed by Terraform

The user says the bucket already exists and should be brought under Terraform.

Use Workflow 2:

- Verify credentials
- Verify bucket region
- Write matching Terraform
- Run:

```bash
terraform import aws_s3_bucket.bucket <bucket_name>
```

- Review drift before applying changes

### Scenario 3: Upload a File

The user wants to upload one file to an existing bucket.

Use Workflow 3:

- Verify credentials
- Verify bucket region
- Run:

```bash
aws s3 cp file.txt s3://<bucket_name>/
```

### Scenario 4: Download a File

The user wants to download a file from an existing bucket.

Use Workflow 3:

- Verify credentials
- Verify bucket region
- Run:

```bash
aws s3 cp s3://<bucket_name>/file.txt .
```

### Scenario 5: Sync a Folder

The user wants to sync a local folder to an existing bucket.

Use Workflow 3:

- Verify credentials
- Verify bucket region
- Run:

```bash
aws s3 sync ./folder s3://<bucket_name>/
```

### Scenario 6: Delete Objects

The user wants to remove data from a bucket.

Treat this as destructive:

- Do not proceed automatically
- Require explicit confirmation
- Restate the scope of deletion before execution

## Summary

Choose the S3 workflow by answering two questions first:

1. Does the bucket already exist?
2. Is the task infrastructure or runtime object work?

Then apply the boundary strictly:

- New managed bucket: Terraform
- Existing bucket to manage: Terraform import and adopt
- Object operations: AWS CLI or SDK

Always verify credentials with:

```bash
aws sts get-caller-identity
```

Always verify existing bucket region with:

```bash
aws s3api get-bucket-location --bucket <bucket_name>
```

Never recreate an existing bucket. Never use Terraform for runtime object operations. Never perform delete operations without explicit confirmation.

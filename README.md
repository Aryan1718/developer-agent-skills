# AWS S3 Skill

Decision-driven agent skill for safe AWS S3 operations.

![type: agent-skill](https://img.shields.io/badge/type-agent--skill-1f2937)
![scope: AWS S3](https://img.shields.io/badge/scope-AWS%20S3-0f766e)
![focus: decision-driven](https://img.shields.io/badge/focus-decision--driven-1d4ed8)

This repository contains a single agent skill for making the right S3 execution decision: create or adopt, Terraform or CLI/SDK, and how to avoid common mistakes before they become incidents.

> [!IMPORTANT]
> This skill enforces a strict boundary:
> - Terraform is only for infrastructure
> - AWS CLI or SDK is only for runtime object operations
> - Existing buckets must be adopted, not recreated
> - AWS credentials and bucket region must be verified first
> - Delete operations are destructive and require explicit confirmation

## What’s Included

- `skills/aws-s3/SKILL.md`  
  The AWS S3 operational skill for AI agents

## Overview

The `aws-s3` skill is built for execution, not theory. It helps an agent choose the correct path before acting:

- create a new bucket only when needed
- adopt an existing bucket instead of recreating it
- use Terraform for infrastructure
- use AWS CLI or SDK for object operations
- verify identity and region before acting
- stop before destructive deletes unless explicitly confirmed

## What Makes This Different

Most S3 guidance focuses on commands. This skill focuses on decisions.

It teaches the agent how to choose the right workflow before running anything:

- create vs adopt
- Terraform vs AWS CLI or SDK
- safe read/write vs destructive delete

That makes it useful for real execution, not just command lookup.

## Decision Summary

- bucket exists → adopt
- bucket does not exist → create with Terraform
- infrastructure → Terraform
- object operations → AWS CLI or SDK
- delete → require explicit confirmation

## What the Skill Does

- decide when a new bucket should be created
- decide when an existing bucket should be adopted
- use Terraform for bucket infrastructure and managed configuration
- use AWS CLI or SDK for object-level operations only
- verify AWS identity before acting
- verify bucket region before operating on existing buckets
- stop before destructive delete actions unless the user explicitly confirms them

## Core Decision Model

The skill keeps S3 work predictable by enforcing this sequence:

1. Verify AWS identity with `aws sts get-caller-identity`
2. Verify bucket region with `aws s3api get-bucket-location --bucket <bucket_name>` when the bucket already exists
3. Decide whether the task is infrastructure or runtime object work
4. Decide whether the bucket should be created or adopted
5. Apply the correct workflow
6. Refuse deletes unless explicit confirmation is provided

## Supported Workflows

### 1. Create Bucket with Terraform

Use this when:

- the task is infrastructure provisioning
- no suitable bucket already exists
- the bucket should be managed as infrastructure

The skill includes Terraform examples for:

- bucket creation
- versioning
- server-side encryption

### 2. Adopt Existing Bucket

Use this when:

- the bucket already exists
- Terraform should manage it going forward
- recreating the bucket would be incorrect or unsafe

This workflow includes importing the bucket into Terraform state:

```bash
terraform import aws_s3_bucket.bucket <bucket_name>
```

### 3. Operate on Bucket Objects

Use this for runtime S3 object operations only, including:

- listing objects
- uploading files
- downloading files
- syncing folders

Example commands covered by the skill:

```bash
aws s3 ls s3://<bucket_name>
aws s3 cp file.txt s3://<bucket_name>/
aws s3 cp s3://<bucket_name>/file.txt .
aws s3 sync ./folder s3://<bucket_name>/
```

## Example Execution

User request:

> “Upload `file.txt` to the existing bucket `team-assets-prod`.”

Agent flow:

1. Verify identity with `aws sts get-caller-identity`
2. Verify bucket region with `aws s3api get-bucket-location --bucket team-assets-prod`
3. Classify the task as runtime object work
4. Choose Workflow 3 instead of Terraform
5. Run the upload command

Final command:

```bash
aws s3 cp file.txt s3://team-assets-prod/
```

## Repository Structure

```text
.
├── README.md
└── skills/
    └── aws-s3/
        └── SKILL.md
```

## Using the Skill

Use this repository when you want an agent to make correct S3 decisions instead of improvising.

Example requests that should trigger this skill:

- “Create a new S3 bucket for this environment with Terraform.”
- “This bucket already exists. Bring it under Terraform.”
- “Upload these files to the existing S3 bucket.”
- “Check which region this bucket is in before we use it.”
- “Should this be done with Terraform or the AWS CLI?”

> [!NOTE]
> The skill is intentionally narrow. It focuses on S3 bucket decisions and operations, not broad AWS architecture or unrelated cloud services.

## Why This Skill Exists

S3 mistakes are usually decision mistakes, not syntax mistakes. Common failures include:

- recreating a bucket that already exists
- using Terraform for object uploads
- using CLI commands to replace infrastructure-as-code
- operating in the wrong AWS account
- operating against the wrong bucket region
- treating destructive deletes like routine commands

This skill exists to reduce those mistakes by giving an agent a clear, safe workflow to follow.

## Safety Guarantees

The skill requires the agent to:

- verify AWS identity before taking action
- verify existing bucket region before operating
- keep infrastructure management and object operations separate
- avoid recreating existing buckets
- stop for explicit confirmation before destructive deletes

## Quick Start

1. Open [`skills/aws-s3/SKILL.md`](skills/aws-s3/SKILL.md).
2. Follow the decision flow to classify the task.
3. Use the matching workflow: create, adopt, or operate.
4. Apply the built-in safety checks before executing commands.

## Summary

This repository provides one focused skill: safe AWS S3 execution for AI agents. If the task involves bucket creation, bucket adoption, Terraform-managed infrastructure, or runtime object operations, the `aws-s3` skill gives the agent a clear path with the right tool boundaries and safety checks.

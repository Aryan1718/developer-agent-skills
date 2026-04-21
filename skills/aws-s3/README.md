# AWS S3 Skill

This skill helps an agent handle AWS S3 work safely. It is designed for tasks
like creating a bucket, adopting an existing bucket into Terraform, or working
with objects in an existing bucket.

## What It Does

- checks AWS identity before acting
- verifies bucket region for existing buckets
- helps choose between create vs adopt
- separates Terraform infrastructure work from CLI or SDK object operations
- requires confirmation before destructive deletes

## How To Use

Use this skill when the task is about S3 bucket decisions or S3 operations.

Examples:

- "Create a new S3 bucket with Terraform"
- "Adopt this existing bucket into Terraform"
- "Upload files to this S3 bucket"
- "Check which region this bucket uses"

Open [SKILL.md](./SKILL.md) and follow the workflow step by step.

# Agent Skills Collection

Production-ready agent skills for three practical workflows: safe AWS S3 execution, Docker container optimization, and guided Git rebasing.

![Type](https://img.shields.io/badge/type-agent%20skills-1f2937)
![Skills](https://img.shields.io/badge/skills-3-0f766e)
![Focus](https://img.shields.io/badge/focus-infra%20%26%20git-1d4ed8)

This repository contains a compact skill bundle intended for practical agent use. Each skill is narrow by design, with explicit decision rules, reusable resources, and safety boundaries that reduce common operational mistakes.

> [!IMPORTANT]
> These skills are built for execution-oriented agents, not generic documentation browsing.
> They are meant to help an agent choose the correct workflow first, then act with the right constraints.

## Included Skills

### `aws-s3`

Decision-driven guidance for AWS S3 tasks where the agent must choose between creating infrastructure, adopting existing resources, or performing object-level operations.

What it covers:

- create vs adopt bucket decisions
- Terraform for infrastructure changes
- AWS CLI or SDK for runtime object operations
- AWS identity verification before acting
- region verification for existing buckets
- explicit confirmation gates for destructive deletes

Examples:

- “Create a new S3 bucket for this environment with Terraform.”
- “This bucket already exists. Bring it under Terraform.”
- “Upload these files to an existing S3 bucket.”
- “Check the bucket region before we use it.”

### `dockerfile-optimizer`

Audit and rewrite support for Dockerfiles and `docker-compose.yml` files, focused on image size, cache efficiency, security, and runtime reliability.

What it covers:

- Dockerfile analysis for security, layering, caching, and image-size issues
- compose analysis for dependency ordering, secret leakage, networking, and resilience gaps
- structured scoring with critical issues, warnings, and suggestions
- full rewritten Dockerfile output
- full rewritten compose output when a compose file is present
- bundled helper scripts and a Docker best-practices reference

Examples:

- “Optimize this Dockerfile.”
- “Why is this image too large?”
- “Audit this docker-compose file.”
- “Check this container setup for security issues.”

### `git-rebase-help`

Guided, safety-first Git rebase support for bringing a branch up to date, handling rebases already in progress, and resolving conflicts block-by-block with explicit confirmation before state-changing actions.

What it covers:

- detect whether a rebase is already in progress
- choose the correct target branch before rebasing
- assess clean versus dirty working tree state
- help the user choose between committing or stashing in-progress work
- start `fetch` plus `rebase` with confirmation gates
- resolve conflicts file-by-file and block-by-block
- continue, skip, or abort safely
- restore stashed work after completion
- remind about safe push behavior with `--force-with-lease`

Examples:

- “Use `git-rebase-help`.”
- “Help me rebase this branch onto main.”
- “Bring this branch up to date with origin/main.”
- “I’m in the middle of a rebase and need conflict help.”

## Repository Structure

```text
.
├── README.md
├── LICENSE
└── skills/
    ├── aws-s3/
    │   └── SKILL.md
    ├── dockerfile-optimizer/
    │   ├── SKILL.md
    │   ├── scripts/
    │   │   ├── analyze_dockerfile.py
    │   │   ├── analyze_compose.py
    │   │   └── generate_report.py
    │   └── references/
    │       └── best_practices.md
    └── git-rebase-help/
        └── SKILL.md
```

## Why This Repo Exists

Infrastructure mistakes usually come from choosing the wrong path before any command runs:

- recreating an S3 bucket that should have been adopted
- using Terraform for object uploads
- copying an entire Docker build context too early
- shipping images that run as root
- exposing services broadly when local binding would be safer

This repository packages skills that force those decisions to be made explicitly.

## How To Use

Open the relevant skill from `skills/` and follow its workflow exactly.

Primary entry points:

- [`skills/aws-s3/SKILL.md`](skills/aws-s3/SKILL.md)
- [`skills/dockerfile-optimizer/SKILL.md`](skills/dockerfile-optimizer/SKILL.md)
- [`skills/git-rebase-help/SKILL.md`](skills/git-rebase-help/SKILL.md)

Typical flow:

1. Match the user request to the correct skill.
2. Load that skill and follow its decision model.
3. Use the bundled scripts when the skill provides them.
4. Preserve the built-in safety checks instead of shortcutting them.

> [!NOTE]
> The skills in this repository are intentionally narrow. They are not broad AWS, Docker, or DevOps playbooks. Their value comes from being opinionated in a few high-risk execution paths.

## Skill Design Principles

The skills here share a consistent design philosophy:

- narrow scope over generic coverage
- decisions before commands
- deterministic helper resources where repetition matters
- clear safety boundaries around destructive or risky actions
- practical output formats that an agent can use directly

## Skill Highlights

### AWS S3

The `aws-s3` skill focuses on operational correctness:

- verify AWS identity first
- verify region for existing buckets
- classify infrastructure work separately from object operations
- adopt existing buckets instead of recreating them
- stop for explicit confirmation before deletes

### Dockerfile Optimization

The `dockerfile-optimizer` skill focuses on container quality:

- catch Dockerfile cache-breaking patterns
- identify security issues such as root users and inline secrets
- flag image bloat and missing multi-stage opportunities
- detect compose reliability and networking issues
- generate a structured optimizer report with rewritten files

### Git Rebase Help

The `git-rebase-help` skill focuses on safe, guided history rewriting:

- verify repository state before rebasing
- choose the correct target branch explicitly
- require a commit-or-stash decision for dirty working trees
- explain rebase conflicts with `HEAD` as target branch state and the other side as the replayed user commit
- require confirmation before `rebase`, `continue`, `skip`, `abort`, `stash pop`, or post-rewrite push steps

## Summary

If the task is safe S3 execution, Dockerfile and compose optimization, or guided Git rebasing, this repository gives an agent a concrete workflow and reusable resources instead of leaving it to improvise.

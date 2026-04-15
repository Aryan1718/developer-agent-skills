# Agent Skills Collection

Focused, production-ready agent skills for common infrastructure and container workflows.

![type: agent-skills](https://img.shields.io/badge/type-agent--skills-1f2937)
![skills: 2](https://img.shields.io/badge/skills-2-0f766e)
![focus: infra](https://img.shields.io/badge/focus-infrastructure-1d4ed8)

This repository packages two narrow, execution-oriented skills:

- `aws-s3` for safe AWS S3 bucket decisions and object operations
- `dockerfile-optimizer` for auditing and rewriting Dockerfile and `docker-compose.yml` files

> [!IMPORTANT]
> These skills are designed for agents that need to act safely and predictably in real projects.
> They emphasize correct workflow selection, explicit safety checks, and complete outputs instead of partial advice.

## Included Skills

### `aws-s3`

Use this skill when the task involves S3 bucket lifecycle or object operations and the agent needs to choose the right path before acting.

Key capabilities:

- decide whether to create a new bucket or adopt an existing one
- separate Terraform-based infrastructure work from AWS CLI or SDK object operations
- verify AWS identity before acting
- verify the region of existing buckets before using them
- require explicit confirmation for destructive deletes

Typical requests:

- “Create a new S3 bucket for this environment with Terraform.”
- “Import this existing bucket into Terraform.”
- “Upload files to this S3 bucket.”
- “Check which region this bucket is in before we use it.”

### `dockerfile-optimizer`

Use this skill when the task involves auditing, optimizing, or fixing a Dockerfile or `docker-compose.yml`.

Key capabilities:

- analyze Dockerfiles for security, caching, image size, and best-practice issues
- analyze compose files for dependency ordering, secret leakage, networking, and reliability gaps
- score findings with critical issues, warnings, and suggestions
- generate a full optimizer report with rewritten Dockerfile and compose output
- provide bundled scripts and a best-practices reference for repeatable analysis

Typical requests:

- “Optimize this Dockerfile.”
- “Why is this image too large?”
- “Audit this docker-compose file.”
- “Check this container setup for security issues.”

## Repository Structure

```text
.
├── README.md
├── LICENSE
└── skills/
    ├── aws-s3/
    │   └── SKILL.md
    └── dockerfile-optimizer/
        ├── SKILL.md
        ├── scripts/
        │   ├── analyze_dockerfile.py
        │   ├── analyze_compose.py
        │   └── generate_report.py
        └── references/
            └── best_practices.md
```

## How To Use

Open the skill directly from the `skills/` directory and invoke it when the request matches its trigger conditions.

Paths:

- [`skills/aws-s3/SKILL.md`](skills/aws-s3/SKILL.md)
- [`skills/dockerfile-optimizer/SKILL.md`](skills/dockerfile-optimizer/SKILL.md)

In practice:

1. Identify whether the task is about S3 operations or Docker/container optimization.
2. Load the matching skill.
3. Follow the skill workflow exactly, including safety checks and required inputs.
4. Use bundled scripts where the skill provides them for deterministic analysis.

## Design Approach

These skills are intentionally narrow. Each one aims to reduce a class of operational mistakes:

- `aws-s3` prevents incorrect bucket handling, wrong tool selection, and unsafe destructive actions
- `dockerfile-optimizer` prevents bloated images, weak container security, broken cache behavior, and fragile compose setups

That narrowness is deliberate. The goal is not broad cloud or DevOps advice. The goal is a reliable execution path for recurring tasks.

## Summary

This repository is a small agent-skill bundle for two high-value infrastructure tasks: safe S3 execution and Dockerfile/compose optimization. If the task is in one of those lanes, the skills here give an agent a concrete workflow and reusable resources instead of improvisation.

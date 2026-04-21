# Agent Skills Collection

A small collection of reusable agent skills for common development workflows.

![Type](https://img.shields.io/badge/type-agent%20skills-1f2937)
![Skills](https://img.shields.io/badge/skills-3-0f766e)
![Focus](https://img.shields.io/badge/focus-dev%20workflows-1d4ed8)

This repository contains a few focused skills that can be dropped into an agent
skill directory and used as building blocks for practical tasks.

## Skills

- `aws-s3` — Safe guidance for AWS S3 bucket decisions and object operations.
- `dockerfile-optimizer` — Audit and rewrite help for Dockerfile and `docker-compose.yml` files.
- `git-rebase-help` — Step-by-step help for safe Git rebasing and conflict resolution.

## Repository Structure

```text
.
├── README.md
├── LICENSE
└── skills/
    ├── aws-s3/
    │   ├── README.md
    │   └── SKILL.md
    ├── dockerfile-optimizer/
    │   ├── README.md
    │   ├── SKILL.md
    │   ├── scripts/
    │   │   ├── analyze_dockerfile.py
    │   │   ├── analyze_compose.py
    │   │   └── generate_report.py
    │   └── references/
    │       └── best_practices.md
    └── git-rebase-help/
        ├── README.md
        └── SKILL.md
```

## Add A Skill

To make a skill available everywhere, copy the skill folder into:

```text
.agents/skills/
```

Example:

```bash
cp -R skills/git-rebase-help ~/.agents/skills/
```

To make a skill available only for one project, copy the skill folder into that
project’s local skill directory:

```text
.codex/skills/
```

Example:

```bash
cp -R skills/git-rebase-help /path/to/project/.codex/skills/
```

Copy the whole folder, not only `SKILL.md`, because some skills may include
extra files such as `scripts/`, `references/`, or a local `README.md`.

## How To Use

1. Add the skill folder to the global or project skill directory.
2. Start the agent in the environment where that skill directory is available.
3. Ask for the task in a way that matches the skill trigger.

Examples:

- `aws-s3`: "Create a new S3 bucket with Terraform"
- `dockerfile-optimizer`: "Optimize this Dockerfile"
- `git-rebase-help`: "Help me rebase this branch onto main"

You can also open the skill directly and review its instructions:

- [`skills/aws-s3/SKILL.md`](skills/aws-s3/SKILL.md)
- [`skills/dockerfile-optimizer/SKILL.md`](skills/dockerfile-optimizer/SKILL.md)
- [`skills/git-rebase-help/SKILL.md`](skills/git-rebase-help/SKILL.md)

## Notes

- Keep each skill folder intact when copying it.
- Use the per-skill `README.md` files for a short overview.
- Use `SKILL.md` for the actual workflow and behavior instructions.

# Dockerfile Optimizer Skill

This skill helps an agent audit and improve `Dockerfile` and
`docker-compose.yml` files. It focuses on security, image size, caching, and
runtime reliability.

## What It Does

- reviews Dockerfile and compose files for common problems
- finds security, performance, and best-practice issues
- scores the current setup
- produces a rewritten optimized version
- uses bundled scripts and references when useful

## How To Use

Use this skill when the task is to audit, optimize, or fix Docker container
configuration files.

Examples:

- "Optimize this Dockerfile"
- "Audit this docker-compose file"
- "Why is this image too large?"
- "Check this container setup for security issues"

Open [SKILL.md](./SKILL.md) and follow the analysis and rewrite flow.

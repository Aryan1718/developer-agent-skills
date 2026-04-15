---
name: dockerfile-optimizer
description: 'Use this skill when the user wants to audit, optimize, or fix a Dockerfile or docker-compose.yml. Triggers on: "optimize Dockerfile", "audit docker", "image too large", "docker security", "check docker-compose", or when Dockerfile or docker-compose.yml files are present in context.'
---

# Dockerfile & Docker Compose Optimizer

## What This Skill Does
Reads existing Dockerfile and docker-compose.yml files, identifies all issues across security, performance, caching, and size, then produces a full rewritten version with a detailed explanation of every change.

## Step-by-Step Instructions

### Step 1 — Read Files
- Read the Dockerfile if present
- Read docker-compose.yml or docker-compose.yaml if present
- If neither exists, ask the user to paste or provide the file

### Step 2 — Analyze Dockerfile for These Exact Issues

LAYER CACHING ISSUES:
- COPY . . placed before npm install / pip install / apt-get (breaks cache on every code change)
- Multiple RUN commands that should be chained with && to reduce layers
- Static assets copied before dependency files

SECURITY VULNERABILITIES:
- No USER directive (container runs as root)
- Hardcoded secrets in ENV (passwords, API keys, tokens)
- Using :latest tag instead of pinned version
- COPY . . without .dockerignore (copies .git, .env, node_modules)
- Packages installed without version pinning
- ARG values that leak into image metadata

IMAGE SIZE BLOAT:
- Large base image (ubuntu/debian when alpine works)
- apt-get without --no-install-recommends flag
- Missing cleanup: && rm -rf /var/lib/apt/lists/*
- Dev dependencies bundled in production image
- No multi-stage build for compiled or build-heavy apps

BEST PRACTICE VIOLATIONS:
- Missing WORKDIR directive
- Missing HEALTHCHECK directive
- Wrong use of CMD vs ENTRYPOINT
- ENV used for build-time values that should be ARG

Use `scripts/analyze_dockerfile.py` when a deterministic issue scan is useful. Read `references/best_practices.md` before rewriting unfamiliar stacks.

### Step 3 — Analyze docker-compose.yml for These Exact Issues

DEPENDENCY ORDERING:
- Missing depends_on between services
- depends_on without condition: service_healthy
- Services referencing each other without declared dependency

ENV VARIABLE LEAKS:
- Hardcoded secrets in environment: block
- No env_file alternative suggested
- Missing .env.example recommendation

RELIABILITY ISSUES:
- Missing restart policy
- No memory or CPU limits
- Unnamed volumes
- Ports bound to 0.0.0.0 unnecessarily

NETWORKING:
- All services on default network without isolation
- Missing explicit network blocks

Use `scripts/analyze_compose.py` when you need a structured compose audit. Load `references/best_practices.md` for rewrite patterns and hardening guidance.

### Step 4 — Score the Files
Start at 100. Deduct:
- 20 points per critical security issue
- 10 points per warning
- 5 points per suggestion
Minimum score is 0.

### Step 5 — Output This Exact Report Format

─────────────────────────────────────────
🐳 DOCKERFILE OPTIMIZER REPORT
─────────────────────────────────────────

📋 SUMMARY
  Critical Issues : X
  Warnings        : X
  Suggestions     : X
  Score           : XX / 100

─────────────────────────────────────────
🔴 CRITICAL ISSUES
─────────────────────────────────────────
[1] <Issue Title>
  Line    : <line number>
  Problem : <why this is dangerous or broken>
  Fix     : <exactly what to change>

─────────────────────────────────────────
🟡 WARNINGS
─────────────────────────────────────────
[same format]

─────────────────────────────────────────
🟢 SUGGESTIONS
─────────────────────────────────────────
[same format]

─────────────────────────────────────────
✅ OPTIMIZED DOCKERFILE
─────────────────────────────────────────
<full rewritten Dockerfile with a comment on every changed line explaining why>

─────────────────────────────────────────
✅ OPTIMIZED DOCKER-COMPOSE.YML
─────────────────────────────────────────
<full rewritten docker-compose.yml — skip this section if no compose file was provided>

─────────────────────────────────────────
📚 WHAT CHANGED & WHY
─────────────────────────────────────────
1. <change> — <one line reason>
2. <change> — <one line reason>
...

Use `scripts/generate_report.py` to render the report. Pass it JSON outputs from the analyzers and, when available, the original file paths so it can synthesize complete rewritten files.

### Step 6 — After Report
Ask the user: "Would you like me to generate an optimized .dockerignore file for this project?"

## Rules
- Always read the actual file, never assume content
- Always output the complete rewritten file, never just diffs
- Never remove functionality, only improve implementation
- If multi-stage build is needed, write the full multi-stage version
- If no docker-compose.yml exists, skip that section silently

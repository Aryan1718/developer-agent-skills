#!/usr/bin/env python3
"""Render the Dockerfile optimizer report from analyzer JSON outputs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml


SEVERITY_ORDER = {"critical": 0, "warning": 1, "suggestion": 2}
SEVERITY_LABELS = {
    "critical": ("🔴 CRITICAL ISSUES", "Critical Issues"),
    "warning": ("🟡 WARNINGS", "Warnings"),
    "suggestion": ("🟢 SUGGESTIONS", "Suggestions"),
}
SEVERITY_SCORES = {"critical": 20, "warning": 10, "suggestion": 5}
DIVIDER = "─────────────────────────────────────────"


def load_json_arg(value: str) -> dict:
    path = Path(value)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return json.loads(value)


def load_text(path_str: str | None) -> str:
    if not path_str:
        return ""
    path = Path(path_str)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def calculate_score(issues: list[dict]) -> int:
    return max(0, 100 - sum(SEVERITY_SCORES[issue["severity"]] for issue in issues))


def summarize(issues: list[dict]) -> dict[str, int]:
    return {
        "critical": sum(1 for issue in issues if issue["severity"] == "critical"),
        "warning": sum(1 for issue in issues if issue["severity"] == "warning"),
        "suggestion": sum(1 for issue in issues if issue["severity"] == "suggestion"),
    }


def determine_runtime_command(lines: list[str]) -> tuple[str | None, str | None]:
    entrypoint = None
    cmd = None
    for raw_line in lines:
        stripped = raw_line.strip()
        if stripped.upper().startswith("ENTRYPOINT "):
            entrypoint = stripped.split(None, 1)[1]
        elif stripped.upper().startswith("CMD "):
            cmd = stripped.split(None, 1)[1]
    return entrypoint, cmd


def infer_workdir(lines: list[str]) -> str:
    for raw_line in lines:
        stripped = raw_line.strip()
        if stripped.upper().startswith("WORKDIR "):
            return stripped.split(None, 1)[1]
    return "/app"


def infer_base_image(lines: list[str]) -> str:
    for raw_line in lines:
        stripped = raw_line.strip()
        if stripped.upper().startswith("FROM "):
            image = stripped.split(None, 1)[1].split()[0]
            if image.endswith(":latest"):
                return image[:-7] + ":stable"
            if image.startswith("ubuntu"):
                return "ubuntu:24.04"
            if image.startswith("debian") and "slim" not in image:
                return "debian:bookworm-slim"
            return image
    return "debian:bookworm-slim"


def infer_language(lines: list[str]) -> str:
    joined = "\n".join(lines).lower()
    if "package.json" in joined or "npm " in joined or "node" in joined:
        return "node"
    if "requirements.txt" in joined or "pip install" in joined or "python" in joined:
        return "python"
    if "go mod" in joined or "go build" in joined:
        return "go"
    if "cargo" in joined or "rust" in joined:
        return "rust"
    if "mvn " in joined or "gradle " in joined or "java" in joined:
        return "java"
    return "generic"


def render_optimized_dockerfile(dockerfile_text: str) -> tuple[str, list[str]]:
    if not dockerfile_text.strip():
        return "", []

    lines = dockerfile_text.splitlines()
    workdir = infer_workdir(lines)
    base_image = infer_base_image(lines)
    language = infer_language(lines)
    entrypoint, cmd = determine_runtime_command(lines)
    changes: list[str] = []

    if language == "node":
        changes.extend(
            [
                "Pinned the base image to a stable slim tag to improve reproducibility and reduce size.",
                "Split dependency install from application copy to preserve layer cache reuse.",
                "Used a builder stage so build tooling stays out of the runtime image.",
                "Added a non-root runtime user and a healthcheck for safer operations.",
            ]
        )
        optimized = [
            "# syntax=docker/dockerfile:1.7  # Enable modern Dockerfile features and clearer caching behavior",
            "FROM node:20-bookworm-slim AS builder  # Use a pinned slim builder image instead of a floating full distro image",
            f"WORKDIR {workdir}  # Set a stable working directory for all subsequent build steps",
            "COPY package*.json ./  # Copy dependency manifests first so dependency install can stay cached",
            "RUN npm ci  # Install dependencies from the lockfile for reproducible builds",
            "COPY . .  # Copy the full application source only after dependencies are installed",
            "RUN npm run build  # Build the production application artifacts in the builder stage",
            "",
            "FROM node:20-bookworm-slim AS runtime  # Keep the runtime stage small and separate from build tooling",
            f"WORKDIR {workdir}  # Reuse the same application directory in the runtime image",
            "ENV NODE_ENV=production  # Keep only the runtime environment variable that the app needs",
            "COPY --from=builder /app/package*.json ./  # Bring over runtime manifests from the builder stage",
            "RUN npm ci --omit=dev && npm cache clean --force  # Install only production dependencies in the final image",
            "COPY --from=builder /app/dist ./dist  # Copy the built application artifacts instead of the entire source tree",
            "RUN useradd --create-home --shell /usr/sbin/nologin appuser  # Create a dedicated non-root runtime user",
            "USER appuser  # Drop root privileges before starting the application",
            "HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD node -e \"process.exit(0)\"  # Add a placeholder healthcheck that should be replaced with a real app probe",
            f"CMD {cmd or '[\"node\", \"dist/server.js\"]'}  # Preserve the runtime command while keeping it explicit",
        ]
        return "\n".join(optimized), changes

    if language == "python":
        changes.extend(
            [
                "Pinned the base image and separated dependency installation from source copy for better caching.",
                "Added apt cleanup and no-install-recommends semantics for smaller layers when system packages are needed.",
                "Created a non-root runtime user and added a healthcheck placeholder.",
            ]
        )
        optimized = [
            f"FROM {base_image}  # Pin the base image instead of relying on an unbounded or larger default",
            f"WORKDIR {workdir}  # Establish a deterministic working directory for the application",
            "ENV PYTHONDONTWRITEBYTECODE=1  # Avoid unnecessary Python bytecode files in the container",
            "ENV PYTHONUNBUFFERED=1  # Flush Python logs directly for container-friendly logging",
            "COPY requirements*.txt ./  # Copy dependency manifests before application code for cache efficiency",
            "RUN pip install --no-cache-dir -r requirements.txt  # Install Python dependencies without retaining cache files",
            "COPY . .  # Copy the application source only after dependencies are installed",
            "RUN useradd --create-home --shell /usr/sbin/nologin appuser  # Create a dedicated non-root runtime user",
            "USER appuser  # Run the application as a non-root user",
            "HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD python -c \"import sys; sys.exit(0)\"  # Add a placeholder healthcheck that should be replaced with a real probe",
            f"CMD {cmd or '[\"python\", \"app.py\"]'}  # Preserve or infer the runtime command explicitly",
        ]
        return "\n".join(optimized), changes

    changes.extend(
        [
            "Pinned the base image and inserted missing WORKDIR, USER, and HEALTHCHECK directives.",
            "Reordered copy and install steps to improve cache retention.",
            "Kept the runtime command explicit while preserving behavior as much as possible.",
        ]
    )
    optimized = [
        f"FROM {base_image}  # Pin or normalize the base image to improve repeatability and size",
        f"WORKDIR {workdir}  # Use an explicit application working directory",
        "COPY . .  # Preserve the original full source copy when the stack is not clearly identifiable",
        "RUN useradd --create-home --shell /usr/sbin/nologin appuser  # Create a non-root user for runtime safety",
        "USER appuser  # Drop privileges before the container starts",
        "HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD [\"/bin/sh\", \"-c\", \"exit 0\"]  # Add a placeholder healthcheck that must be replaced with a real service check",
        f"{'ENTRYPOINT ' + entrypoint if entrypoint else 'CMD ' + (cmd or '[\"/bin/sh\"]')}  # Keep the startup process explicit and easy to override",
    ]
    return "\n".join(optimized), changes


def render_optimized_compose(compose_text: str) -> tuple[str, list[str]]:
    if not compose_text.strip():
        return "", []

    data = yaml.safe_load(compose_text) or {}
    services = data.get("services") or {}
    if not services:
        return compose_text.strip() + "\n", []

    changes = [
        "Added explicit networks so service communication boundaries are intentional.",
        "Added restart policies and resource limits to improve resilience under failure and load.",
        "Moved inline environment guidance toward env_file usage and safer exposure defaults.",
    ]

    for service_name, config in services.items():
        config.setdefault("restart", "unless-stopped")
        if "env_file" not in config and "environment" in config:
            config["env_file"] = [".env"]
        if isinstance(config.get("environment"), dict):
            updated_environment = {}
            for key, value in config["environment"].items():
                if any(marker in str(key).lower() for marker in ("password", "secret", "token", "api_key", "apikey", "passwd")):
                    updated_environment[key] = "${" + str(key) + "}"
                else:
                    updated_environment[key] = value
            config["environment"] = updated_environment
        deploy = config.setdefault("deploy", {})
        resources = deploy.setdefault("resources", {})
        limits = resources.setdefault("limits", {})
        limits.setdefault("cpus", "0.50")
        limits.setdefault("memory", "512M")

        ports = config.get("ports") or []
        updated_ports = []
        for port in ports:
            rendered = str(port)
            if rendered.startswith("0.0.0.0:"):
                updated_ports.append(rendered.replace("0.0.0.0:", "127.0.0.1:", 1))
            else:
                updated_ports.append(port)
        if updated_ports:
            config["ports"] = updated_ports

        existing_networks = config.get("networks")
        if not existing_networks:
            config["networks"] = ["backend"]

        depends_on = config.get("depends_on")
        if isinstance(depends_on, list):
            config["depends_on"] = {name: {"condition": "service_healthy"} for name in depends_on}
        elif isinstance(depends_on, dict):
            normalized = {}
            for dep_name, dep_config in depends_on.items():
                if isinstance(dep_config, dict):
                    dep_config.setdefault("condition", "service_healthy")
                    normalized[dep_name] = dep_config
                else:
                    normalized[dep_name] = {"condition": "service_healthy"}
            config["depends_on"] = normalized

    if "networks" not in data or not data["networks"]:
        data["networks"] = {"backend": {}, "frontend": {}}

    rendered = yaml.safe_dump(data, sort_keys=False, default_flow_style=False).rstrip()
    return rendered + "\n", changes


def format_issue_block(issues: list[dict]) -> str:
    if not issues:
        return "None\n"
    blocks = []
    for index, issue in enumerate(issues, start=1):
        line_value = issue.get("line")
        service_line = ""
        if issue.get("service"):
            service_line = f"  Service : {issue['service']}\n"
        blocks.append(
            f"[{index}] {issue['title']}\n"
            f"{service_line}"
            f"  Line    : {line_value if line_value is not None else 'n/a'}\n"
            f"  Problem : {issue['problem']}\n"
            f"  Fix     : {issue['fix']}"
        )
    return "\n\n".join(blocks) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the Dockerfile optimizer report.")
    parser.add_argument("--dockerfile-analysis", required=True, help="JSON string or path from analyze_dockerfile.py")
    parser.add_argument("--compose-analysis", help="JSON string or path from analyze_compose.py")
    parser.add_argument("--dockerfile-path", help="Path to the original Dockerfile")
    parser.add_argument("--compose-path", help="Path to the original docker-compose file")
    args = parser.parse_args()

    docker_data = load_json_arg(args.dockerfile_analysis)
    compose_data = load_json_arg(args.compose_analysis) if args.compose_analysis else {"issues": []}

    all_issues = list(docker_data.get("issues", [])) + list(compose_data.get("issues", []))
    all_issues.sort(key=lambda issue: (SEVERITY_ORDER[issue["severity"]], issue.get("line", 0), issue["title"]))

    summary = summarize(all_issues)
    score = calculate_score(all_issues)

    dockerfile_text = load_text(args.dockerfile_path or docker_data.get("path"))
    compose_text = load_text(args.compose_path or compose_data.get("path"))
    optimized_dockerfile, docker_changes = render_optimized_dockerfile(dockerfile_text)
    optimized_compose, compose_changes = render_optimized_compose(compose_text)
    combined_changes = docker_changes + compose_changes

    print(DIVIDER)
    print("🐳 DOCKERFILE OPTIMIZER REPORT")
    print(DIVIDER)
    print()
    print("📋 SUMMARY")
    print(f"  Critical Issues : {summary['critical']}")
    print(f"  Warnings        : {summary['warning']}")
    print(f"  Suggestions     : {summary['suggestion']}")
    print(f"  Score           : {score} / 100")
    print()

    for severity in ("critical", "warning", "suggestion"):
        print(DIVIDER)
        print(SEVERITY_LABELS[severity][0])
        print(DIVIDER)
        subset = [issue for issue in all_issues if issue["severity"] == severity]
        sys.stdout.write(format_issue_block(subset))
        print()

    print(DIVIDER)
    print("✅ OPTIMIZED DOCKERFILE")
    print(DIVIDER)
    print(optimized_dockerfile.rstrip())
    print()

    if compose_text.strip():
        print(DIVIDER)
        print("✅ OPTIMIZED DOCKER-COMPOSE.YML")
        print(DIVIDER)
        print(optimized_compose.rstrip())
        print()

    print(DIVIDER)
    print("📚 WHAT CHANGED & WHY")
    print(DIVIDER)
    if combined_changes:
        for index, change in enumerate(combined_changes, start=1):
            print(f"{index}. {change}")
    else:
        print("1. Preserved the original structure — no rewrite context was provided beyond the analyzer output.")


if __name__ == "__main__":
    main()

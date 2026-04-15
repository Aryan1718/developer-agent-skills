#!/usr/bin/env python3
"""Analyze a docker-compose YAML file for reliability and security issues."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import yaml


CRITICAL = "critical"
WARNING = "warning"
SUGGESTION = "suggestion"
SECRET_PATTERN = re.compile(r"(password|secret|token|api[_-]?key|passwd)", re.IGNORECASE)
SERVICE_REF_PATTERN = re.compile(r"\b([a-zA-Z0-9_-]+):\d+\b")


def make_issue(severity: str, service: str, line: int, title: str, problem: str, fix: str) -> dict:
    return {
        "severity": severity,
        "service": service,
        "line": line,
        "title": title,
        "problem": problem,
        "fix": fix,
    }


def find_line(lines: list[str], service: str, field: str | None = None) -> int:
    service_pattern = re.compile(rf"^\s{{2}}{re.escape(service)}:\s*$")
    field_pattern = re.compile(rf"^\s{{4}}{re.escape(field)}:\s*$") if field else None
    inside_service = False
    for number, line in enumerate(lines, start=1):
        if service_pattern.match(line):
            inside_service = True
            if field is None:
                return number
            continue
        if inside_service:
            if re.match(r"^\s{2}[A-Za-z0-9_-]+:\s*$", line):
                inside_service = False
            elif field_pattern and field_pattern.match(line):
                return number
    return 1


def normalize_environment(environment) -> dict[str, str]:
    if environment is None:
        return {}
    if isinstance(environment, dict):
        return {str(key): "" if value is None else str(value) for key, value in environment.items()}
    if isinstance(environment, list):
        result: dict[str, str] = {}
        for item in environment:
            if isinstance(item, str) and "=" in item:
                key, value = item.split("=", 1)
                result[key] = value
            elif isinstance(item, str):
                result[item] = ""
        return result
    return {}


def dependency_candidates(services: dict) -> dict[str, set[str]]:
    names = set(services)
    mapping: dict[str, set[str]] = {name: set() for name in services}
    for service_name, config in services.items():
        serialized = json.dumps(config)
        for candidate in names - {service_name}:
            if candidate in serialized:
                mapping[service_name].add(candidate)
        for match in SERVICE_REF_PATTERN.findall(serialized):
            if match in names and match != service_name:
                mapping[service_name].add(match)
    return mapping


def analyze(compose_path: Path) -> dict:
    lines = compose_path.read_text(encoding="utf-8").splitlines()
    data = yaml.safe_load("\n".join(lines)) or {}
    services = data.get("services") or {}
    issues: list[dict] = []

    named_networks = data.get("networks") or {}
    top_level_volumes = data.get("volumes") or {}
    inferred_dependencies = dependency_candidates(services)

    if services and not named_networks:
        issues.append(
            make_issue(
                WARNING,
                "*",
                1,
                "Missing Explicit Network Blocks",
                "All services rely on the implicit default network, which makes segmentation and intent less clear.",
                "Define explicit networks and attach services only to the networks they need.",
            )
        )
        if len(services) > 1:
            issues.append(
                make_issue(
                    SUGGESTION,
                    "*",
                    1,
                    "Default Network Without Isolation",
                    "Multiple services appear to share the default network without any isolation boundaries.",
                    "Add named frontend/backend networks or equivalent service-specific isolation.",
                )
            )

    if services and ".env.example" not in {path.name for path in compose_path.parent.iterdir() if path.is_file()}:
        issues.append(
            make_issue(
                SUGGESTION,
                "*",
                1,
                "Missing .env.example Recommendation",
                "Projects using compose should usually provide a sanitized .env.example for onboarding and secret management.",
                "Create a .env.example file with placeholder values and document required variables.",
            )
        )

    for service_name, config in services.items():
        service_line = find_line(lines, service_name)
        depends_on = config.get("depends_on")
        declared_dependencies: set[str] = set()

        if isinstance(depends_on, list):
            declared_dependencies = {str(item) for item in depends_on}
            issues.append(
                make_issue(
                    WARNING,
                    service_name,
                    find_line(lines, service_name, "depends_on"),
                    "depends_on Without service_healthy Conditions",
                    "List-style depends_on only controls startup order and does not wait for dependency health.",
                    "Use mapping-style depends_on with condition: service_healthy for stateful dependencies.",
                )
            )
        elif isinstance(depends_on, dict):
            declared_dependencies = {str(item) for item in depends_on}
            for dep_name, dep_config in depends_on.items():
                if not isinstance(dep_config, dict) or dep_config.get("condition") != "service_healthy":
                    issues.append(
                        make_issue(
                            WARNING,
                            service_name,
                            find_line(lines, service_name, "depends_on"),
                            "depends_on Missing service_healthy Condition",
                            f"{service_name} depends on {dep_name} but does not explicitly wait for a healthy dependency.",
                            "Set depends_on.<service>.condition to service_healthy and add healthchecks to upstream services.",
                        )
                    )

        inferred = inferred_dependencies.get(service_name, set())
        missing_declared = inferred - declared_dependencies
        if missing_declared:
            issues.append(
                make_issue(
                    WARNING,
                    service_name,
                    service_line,
                    "Missing depends_on",
                    f"{service_name} references {', '.join(sorted(missing_declared))} but does not declare all dependencies.",
                    "Add depends_on entries for referenced services and prefer service_healthy conditions.",
                )
            )

        environment = normalize_environment(config.get("environment"))
        if environment:
            for key, value in environment.items():
                if SECRET_PATTERN.search(key) and value:
                    issues.append(
                        make_issue(
                            CRITICAL,
                            service_name,
                            find_line(lines, service_name, "environment"),
                            "Hardcoded Secret in environment",
                            f"{service_name} defines {key} inline, which can leak credentials into version control and local logs.",
                            "Move secret values to env_file, Docker secrets, or a secret manager and keep placeholders in compose.",
                        )
                    )
                    break
            if "env_file" not in config:
                issues.append(
                    make_issue(
                        SUGGESTION,
                        service_name,
                        find_line(lines, service_name, "environment"),
                        "No env_file Alternative Suggested",
                        "Inline environment blocks are harder to manage across environments and encourage committing secrets.",
                        "Add env_file for non-secret configuration and document runtime-secret handling separately.",
                    )
                )

        if "restart" not in config:
            issues.append(
                make_issue(
                    WARNING,
                    service_name,
                    service_line,
                    "Missing Restart Policy",
                    "Without a restart policy, transient failures may leave the service down until manual intervention.",
                    "Add restart: unless-stopped or another policy appropriate for the service.",
                )
            )

        deploy = config.get("deploy") or {}
        resources = deploy.get("resources") if isinstance(deploy, dict) else None
        limits = resources.get("limits") if isinstance(resources, dict) else None
        has_memory_limit = bool(config.get("mem_limit")) or bool(isinstance(limits, dict) and limits.get("memory"))
        has_cpu_limit = bool(config.get("cpus")) or bool(isinstance(limits, dict) and limits.get("cpus"))
        if not has_memory_limit or not has_cpu_limit:
            issues.append(
                make_issue(
                    WARNING,
                    service_name,
                    service_line,
                    "Missing Memory or CPU Limits",
                    "Services without resource limits can starve other workloads or destabilize the host under load.",
                    "Define memory and CPU limits using compose fields supported by your deployment target.",
                )
            )

        for volume in config.get("volumes") or []:
            if isinstance(volume, str):
                source = volume.split(":", 1)[0]
                if source.startswith("/") or source.startswith("."):
                    continue
                if source not in top_level_volumes:
                    issues.append(
                        make_issue(
                            SUGGESTION,
                            service_name,
                            find_line(lines, service_name, "volumes"),
                            "Unnamed Volume",
                            "A service references a volume-like source that is not declared at the top level, which makes intent and reuse less clear.",
                            "Declare named volumes in the top-level volumes block and reference them from services.",
                        )
                    )
                    break

        for port in config.get("ports") or []:
            rendered = str(port)
            if rendered.startswith("0.0.0.0:"):
                issues.append(
                    make_issue(
                        WARNING,
                        service_name,
                        find_line(lines, service_name, "ports"),
                        "Port Bound to 0.0.0.0",
                        "Binding directly to 0.0.0.0 exposes the service on every interface even when local-only access would be sufficient.",
                        "Bind to 127.0.0.1 where possible or document why external exposure is required.",
                    )
                )
                break

    return {
        "path": str(compose_path),
        "issues": issues,
        "summary": {
            "critical": sum(1 for issue in issues if issue["severity"] == CRITICAL),
            "warning": sum(1 for issue in issues if issue["severity"] == WARNING),
            "suggestion": sum(1 for issue in issues if issue["severity"] == SUGGESTION),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze a docker-compose.yml file for issues.")
    parser.add_argument("compose_file", help="Path to docker-compose.yml or docker-compose.yaml.")
    args = parser.parse_args()

    compose_path = Path(args.compose_file)
    result = analyze(compose_path)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Analyze a Dockerfile for common security, caching, and size issues."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


CRITICAL = "critical"
WARNING = "warning"
SUGGESTION = "suggestion"
SEVERITY_SCORES = {CRITICAL: 20, WARNING: 10, SUGGESTION: 5}
SECRET_PATTERN = re.compile(r"(password|secret|token|api[_-]?key|passwd)", re.IGNORECASE)


def make_issue(severity: str, line: int, title: str, problem: str, fix: str) -> dict:
    return {
        "severity": severity,
        "line": line,
        "title": title,
        "problem": problem,
        "fix": fix,
    }


def detect_package_manager_install(command: str) -> bool:
    lowered = command.lower()
    return any(token in lowered for token in ("npm install", "pip install", "apt-get install", "apk add", "go mod download", "cargo build", "mvn package", "gradle build"))


def is_dependency_copy(argument: str) -> bool:
    lowered = argument.lower()
    markers = (
        "package.json",
        "package-lock.json",
        "pnpm-lock.yaml",
        "yarn.lock",
        "requirements.txt",
        "poetry.lock",
        "pyproject.toml",
        "go.mod",
        "go.sum",
        "cargo.toml",
        "cargo.lock",
        "pom.xml",
        "build.gradle",
        "composer.json",
        "composer.lock",
    )
    return any(marker in lowered for marker in markers)


def analyze(lines: list[str], dockerfile_path: Path) -> dict:
    issues: list[dict] = []
    from_line = 0
    workdir_line = 0
    user_line = 0
    healthcheck_line = 0
    copy_all_line = 0
    copy_all_before_install = 0
    run_lines: list[tuple[int, str]] = []
    install_lines: list[int] = []
    dependency_copy_seen = False
    env_lines: list[tuple[int, str]] = []
    arg_lines: list[tuple[int, str]] = []
    entrypoint_line = 0
    cmd_line = 0

    dockerignore_exists = (dockerfile_path.parent / ".dockerignore").exists()

    for number, raw_line in enumerate(lines, start=1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        parts = stripped.split(None, 1)
        instruction = parts[0].upper()
        argument = parts[1] if len(parts) > 1 else ""
        lowered = argument.lower()

        if instruction == "FROM" and not from_line:
            from_line = number
            image_ref = argument.split()[0]
            if ":latest" in image_ref:
                issues.append(
                    make_issue(
                        CRITICAL,
                        number,
                        "Unpinned Base Image",
                        "Using a latest tag makes builds non-reproducible and may pull unexpected image changes.",
                        "Replace :latest with a specific version tag or immutable digest.",
                    )
                )
            if image_ref.startswith(("ubuntu", "debian")) and "slim" not in image_ref and "distroless" not in image_ref:
                issues.append(
                    make_issue(
                        WARNING,
                        number,
                        "Large Base Image",
                        "A full ubuntu/debian base often increases attack surface and image size.",
                        "Consider debian-slim, alpine, or distroless if the application supports it.",
                    )
                )

        elif instruction == "WORKDIR":
            workdir_line = number
        elif instruction == "USER":
            user_line = number
        elif instruction == "HEALTHCHECK":
            healthcheck_line = number
        elif instruction == "ENTRYPOINT":
            entrypoint_line = number
        elif instruction == "CMD":
            cmd_line = number
        elif instruction == "COPY":
            normalized = re.sub(r"\s+", " ", lowered).strip()
            if normalized in {". .", "./ .", ". /app", "./ /app"} and not copy_all_line:
                copy_all_line = number
                if not dockerignore_exists:
                    issues.append(
                        make_issue(
                            CRITICAL,
                            number,
                            "COPY . . Without .dockerignore",
                            "Copying the full build context without a .dockerignore may include .git, .env, and dependency directories.",
                            "Add a .dockerignore file and copy only the files needed for each build step.",
                        )
                    )
            if is_dependency_copy(argument):
                dependency_copy_seen = True
            if copy_all_line and detect_package_manager_install(argument):
                copy_all_before_install = copy_all_line
        elif instruction == "RUN":
            run_lines.append((number, argument))
            if detect_package_manager_install(argument):
                install_lines.append(number)
                if copy_all_line and copy_all_line < number and not dependency_copy_seen:
                    copy_all_before_install = copy_all_line

            if "apt-get install" in lowered:
                if "--no-install-recommends" not in lowered:
                    issues.append(
                        make_issue(
                            WARNING,
                            number,
                            "apt-get Install Without --no-install-recommends",
                            "Recommended packages can pull in unnecessary dependencies and increase the final image size.",
                            "Add --no-install-recommends to apt-get install commands.",
                        )
                    )
                if "rm -rf /var/lib/apt/lists" not in lowered:
                    issues.append(
                        make_issue(
                            WARNING,
                            number,
                            "Missing apt Cache Cleanup",
                            "Package index files stay in the layer and bloat the image when apt metadata is not removed.",
                            "Chain apt-get install with rm -rf /var/lib/apt/lists/* in the same RUN instruction.",
                        )
                    )
                install_args = re.findall(r"apt-get install(?:[^\n\\;&]|\\.)*", argument)
                for chunk in install_args:
                    tokens = [token for token in re.split(r"\s+", chunk) if token and not token.startswith("-")]
                    package_tokens = [token for token in tokens if token not in {"apt-get", "install"}]
                    unpinned = [token for token in package_tokens if "=" not in token]
                    if unpinned:
                        issues.append(
                            make_issue(
                                SUGGESTION,
                                number,
                                "Unpinned apt Packages",
                                "Unpinned packages can change across builds and affect reproducibility.",
                                "Pin package versions where practical or document why floating versions are acceptable.",
                            )
                        )
                        break

            if "npm install" in lowered and "npm ci" not in lowered:
                issues.append(
                    make_issue(
                        WARNING,
                        number,
                        "npm install Used in Production Build",
                        "npm install can drift from the lockfile and is slower than npm ci in CI or container builds.",
                        "Use npm ci after copying package manifests and lockfiles.",
                    )
                )
            if "pip install" in lowered and "-r" in lowered and "requirements.txt" in lowered and "==" not in lowered:
                issues.append(
                    make_issue(
                        SUGGESTION,
                        number,
                        "Potentially Unpinned Python Dependencies",
                        "requirements.txt appears to be installed without visible version guarantees in the Dockerfile.",
                        "Ensure requirements.txt pins versions and keep it separate from application source copies.",
                    )
                )
        elif instruction == "ENV":
            env_lines.append((number, argument))
            if SECRET_PATTERN.search(argument):
                issues.append(
                    make_issue(
                        CRITICAL,
                        number,
                        "Hardcoded Secret in ENV",
                        "Secrets in Dockerfile ENV instructions are baked into image metadata and layer history.",
                        "Move secrets to runtime environment variables or a secret manager and keep placeholders out of the image.",
                    )
                )
            if any(marker in lowered for marker in ("build_", "version=", "commit=", "sha=", "branch=")):
                issues.append(
                    make_issue(
                        SUGGESTION,
                        number,
                        "ENV Used for Build-Time Value",
                        "Build metadata set with ENV persists into runtime even when it is only needed during build.",
                        "Use ARG for build-time values and only promote to ENV when the runtime truly needs it.",
                    )
                )
        elif instruction == "ARG":
            arg_lines.append((number, argument))
            if SECRET_PATTERN.search(argument):
                issues.append(
                    make_issue(
                        CRITICAL,
                        number,
                        "Sensitive ARG Value",
                        "Secrets passed through ARG may leak through image history or build metadata.",
                        "Do not embed secrets in ARG defaults; inject them at build time through secure secret mechanisms.",
                    )
                )

    if copy_all_before_install:
        issues.append(
            make_issue(
                WARNING,
                copy_all_before_install,
                "COPY . . Before Dependency Installation",
                "Copying the entire source tree before dependency installation breaks cache reuse on every code change.",
                "Copy dependency manifests first, install dependencies, then copy the remaining application files.",
            )
        )

    if len(run_lines) > 1:
        sequential_runs = 0
        previous_line = 0
        for line_number, _ in run_lines:
            if previous_line and line_number == previous_line + 1:
                sequential_runs += 1
            previous_line = line_number
        if sequential_runs or len(run_lines) >= 3:
            issues.append(
                make_issue(
                    SUGGESTION,
                    run_lines[0][0],
                    "Multiple RUN Layers",
                    "Several RUN instructions can often be merged to reduce image layers and keep cleanup in the same layer.",
                    "Combine related RUN commands with && when it does not reduce readability or change behavior.",
                )
            )

    if install_lines and not user_line:
        issues.append(
            make_issue(
                CRITICAL,
                from_line or 1,
                "Container Runs as Root",
                "Without a USER directive the container process runs as root, increasing blast radius if compromised.",
                "Create a non-root user and switch to it before the final CMD or ENTRYPOINT.",
            )
        )
    elif not user_line:
        issues.append(
            make_issue(
                CRITICAL,
                from_line or 1,
                "Container Runs as Root",
                "No USER directive was found, so the runtime user defaults to root.",
                "Create a dedicated non-root user and add USER before the runtime command.",
            )
        )

    if not workdir_line:
        issues.append(
            make_issue(
                WARNING,
                from_line or 1,
                "Missing WORKDIR",
                "Without WORKDIR, COPY, RUN, and startup commands depend on the default filesystem location.",
                "Add a WORKDIR directive before COPY and RUN steps.",
            )
        )

    if not healthcheck_line:
        issues.append(
            make_issue(
                SUGGESTION,
                cmd_line or entrypoint_line or from_line or 1,
                "Missing HEALTHCHECK",
                "Containers without a healthcheck are harder to supervise and restart safely in orchestrated environments.",
                "Add a HEALTHCHECK command that validates the service is ready to receive traffic.",
            )
        )

    if cmd_line and not entrypoint_line:
        issues.append(
            make_issue(
                SUGGESTION,
                cmd_line,
                "Review CMD vs ENTRYPOINT Usage",
                "A standalone CMD is valid, but long-running app containers often benefit from an ENTRYPOINT plus default CMD arguments.",
                "Confirm whether the image should always run a fixed process via ENTRYPOINT with CMD for defaults.",
            )
        )

    if len([line for line, arg in env_lines if SECRET_PATTERN.search(arg)]) == 0 and arg_lines:
        for line_number, argument in arg_lines:
            if "=" in argument and SECRET_PATTERN.search(argument.split("=", 1)[0]):
                break

    if any(
        token in "\n".join(lines).lower()
        for token in ("npm run build", "go build", "cargo build", "mvn package", "gradle build", "pip install", "poetry install")
    ) and sum(1 for raw in lines if raw.strip().upper().startswith("FROM ")) < 2:
        issues.append(
            make_issue(
                WARNING,
                from_line or 1,
                "No Multi-Stage Build",
                "Build-heavy applications usually benefit from a separate builder stage to keep toolchains and dev artifacts out of the runtime image.",
                "Split the Dockerfile into builder and runtime stages while preserving the current behavior.",
            )
        )

    if any(marker in "\n".join(lines).lower() for marker in ("npm install", "pip install -r requirements-dev", "poetry install", "apk add build-base")):
        issues.append(
            make_issue(
                SUGGESTION,
                install_lines[0] if install_lines else (from_line or 1),
                "Review Production Dependency Scope",
                "The Dockerfile may be installing build or development dependencies into the final image.",
                "Limit the runtime stage to production dependencies only, especially in multi-stage builds.",
            )
        )

    summary = {
        "critical": sum(1 for issue in issues if issue["severity"] == CRITICAL),
        "warning": sum(1 for issue in issues if issue["severity"] == WARNING),
        "suggestion": sum(1 for issue in issues if issue["severity"] == SUGGESTION),
    }
    score = max(0, 100 - sum(SEVERITY_SCORES[issue["severity"]] for issue in issues))

    return {
        "path": str(dockerfile_path),
        "issues": issues,
        "summary": summary,
        "score": score,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze a Dockerfile for optimization issues.")
    parser.add_argument("dockerfile", help="Path to the Dockerfile to analyze.")
    args = parser.parse_args()

    dockerfile_path = Path(args.dockerfile)
    lines = dockerfile_path.read_text(encoding="utf-8").splitlines()
    result = analyze(lines, dockerfile_path)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

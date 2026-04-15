# Docker Best Practices Reference

## Contents
- Multi-stage build patterns
- Base image size comparison
- Layer caching order rule
- Docker security hardening checklist
- Links

## Multi-Stage Build Patterns

### Node.js
```dockerfile
FROM node:20-bookworm-slim AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci

FROM deps AS build
COPY . .
RUN npm run build

FROM node:20-bookworm-slim AS runtime
WORKDIR /app
ENV NODE_ENV=production
COPY --from=deps /app/package*.json ./
RUN npm ci --omit=dev && npm cache clean --force
COPY --from=build /app/dist ./dist
USER node
CMD ["node", "dist/server.js"]
```

### Python
```dockerfile
FROM python:3.12-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

FROM python:3.12-slim AS runtime
WORKDIR /app
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*
COPY . .
USER 10001
CMD ["python", "app.py"]
```

### Go
```dockerfile
FROM golang:1.22-bookworm AS builder
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o /out/app ./cmd/app

FROM gcr.io/distroless/static-debian12
COPY --from=builder /out/app /app
USER nonroot:nonroot
ENTRYPOINT ["/app"]
```

### Java
```dockerfile
FROM maven:3.9-eclipse-temurin-21 AS builder
WORKDIR /workspace
COPY pom.xml .
RUN mvn -q -DskipTests dependency:go-offline
COPY . .
RUN mvn -q -DskipTests package

FROM eclipse-temurin:21-jre-jammy
WORKDIR /app
COPY --from=builder /workspace/target/app.jar ./app.jar
USER 10001
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
```

### Rust
```dockerfile
FROM rust:1.77-bookworm AS builder
WORKDIR /workspace
COPY Cargo.toml Cargo.lock ./
COPY src ./src
RUN cargo build --release

FROM debian:bookworm-slim
WORKDIR /app
COPY --from=builder /workspace/target/release/app ./app
RUN useradd --create-home --shell /usr/sbin/nologin appuser
USER appuser
ENTRYPOINT ["./app"]
```

## Base Image Size Comparison

| Base image | Approx compressed size | Pros | Tradeoffs |
| --- | ---: | --- | --- |
| `ubuntu:24.04` | ~77 MB | Broad package ecosystem, familiar tooling | Largest footprint, more CVE surface |
| `debian:bookworm` | ~48 MB | Stable general-purpose base | Larger than slim variants |
| `debian:bookworm-slim` | ~22 MB | Good balance of compatibility and size | Fewer preinstalled tools |
| `alpine:3.20` | ~7 MB | Very small, quick pulls | musl libc can break some binaries |
| `distroless` | ~2-15 MB | Minimal runtime attack surface | Harder debugging, no package manager or shell |

## Layer Caching Order Rule

Build from least-changing inputs to most-changing inputs:

1. Base image and OS packages
2. Tooling and package manager setup
3. Dependency manifests (`package-lock.json`, `requirements.txt`, `go.sum`, `Cargo.lock`)
4. Dependency installation
5. Application source code
6. Build output generation
7. Runtime-only configuration

Rule of thumb: copy only the files needed for each step, and delay `COPY . .` until the latest reasonable point.

## 20-Item Docker Security Hardening Checklist

1. Pin base images to a specific version or digest.
2. Prefer slim or distroless runtime images.
3. Add a non-root runtime user with `USER`.
4. Avoid hardcoded secrets in `ENV`, `ARG`, or compose files.
5. Use `.dockerignore` to exclude secrets, VCS data, and local artifacts.
6. Keep package installs minimal and explicit.
7. Use `--no-install-recommends` with `apt-get install`.
8. Remove package manager caches in the same layer.
9. Split build and runtime stages with multi-stage builds.
10. Install only production dependencies in the final stage.
11. Add `HEALTHCHECK` for long-running services.
12. Prefer exec-form `CMD` and `ENTRYPOINT`.
13. Expose only required ports.
14. Bind host ports to `127.0.0.1` unless external access is required.
15. Set memory and CPU limits in compose or orchestration config.
16. Use read-only filesystems where the app supports it.
17. Drop Linux capabilities that the service does not need.
18. Avoid privileged mode and host namespace sharing.
19. Scan images for vulnerabilities before release.
20. Keep base images and dependencies patched on a defined schedule.

## Links

- https://docs.docker.com/develop/develop-images/dockerfile_best-practices/
- https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html

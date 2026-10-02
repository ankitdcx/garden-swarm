# Build from garden-runtime: docker build -f deploy/Dockerfile .
# The model never sees the gate image's policy/state/credentials.
FROM rust:1.90-slim-bookworm AS kernel-build
WORKDIR /build
COPY garden-kernel/Cargo.toml garden-kernel/Cargo.lock ./
COPY garden-kernel/src ./src
RUN cargo build --locked --release

FROM python:3.12-slim-bookworm AS advisory
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/opt/garden/garden-agents:/opt/garden/garden-lang
WORKDIR /opt/garden
COPY garden-agents ./garden-agents
COPY garden-lang ./garden-lang
RUN chmod -R a-w /opt/garden
USER 65534:65534
ENTRYPOINT ["python","-m","garden_agents"]


FROM python:3.12-slim-bookworm AS controller
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /opt/garden
COPY --from=kernel-build /build/target/release/garden-gate /opt/garden/bin/garden-gate
COPY garden-console ./garden-console
COPY garden-gate/config ./garden-gate/config
COPY garden-agents ./garden-agents
COPY garden-lang ./garden-lang
COPY docs/source-map.json ./docs/source-map.json
RUN mkdir -p /var/lib/garden && chmod 700 /var/lib/garden && chmod -R a-w /opt/garden
# Trusted controller needs SETUID/SETGID solely to drop advisory workers to nobody.
# Compose strips every other capability and prevents agent access to /var/lib/garden.
USER 0:0
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --retries=3 CMD ["python","-c","import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/api/health',timeout=2)"]
ENTRYPOINT ["python","garden-console/server.py","--host","0.0.0.0","--port","8080","--gate","/opt/garden/bin/garden-gate","--state","/var/lib/garden"]

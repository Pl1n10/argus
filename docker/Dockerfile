# argus — single-container backup observability.
#
# One image, SQLite inside a mounted volume, server-rendered UI. Runs identical
# on an RPi (arm64), a VPS, or the homelab (amd64). The whole product promise is
# "docker run, open browser" — so this stays one slim stage, no node build, no
# second service. See DECISIONS.md D-002 / D-003.
#
#   docker build -t argus-backup -f docker/Dockerfile .
#   docker run --rm -p 8000:8000 -v argus-data:/data argus-backup
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    ARGUS_DB=/data/argus.db

WORKDIR /app

# Dependency metadata first so the pip layer caches until deps actually change.
COPY pyproject.toml README.md ./
COPY argus/ ./argus/
RUN pip install .

# SQLite file lives in the mounted volume, not the image.
RUN mkdir -p /data
VOLUME ["/data"]

EXPOSE 8000

# slim has no curl; probe with the stdlib instead.
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python3 -c "import urllib.request,sys; \
        sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health').status==200 else 1)" \
        || exit 1

# 0.0.0.0 because we are in a container (LAN / Cloudflare Tunnel reach it).
CMD ["sh", "-c", "argus serve --host 0.0.0.0 --port 8000 --db ${ARGUS_DB}"]

# Runtime pins are deliberately exact. The Python, uv, and Deno images are official
# multi-architecture images; FFmpeg is the exact Debian bookworm security build audited in
# THIRD_PARTY_NOTICES.md. Runtime startup performs no package or executable downloads.
ARG PYTHON_IMAGE=python:3.13.15-slim-bookworm@sha256:ed86c82274b3c69b52fb5820f358f0bd7df0b603332063cb5c6e32bd220c3e6e
ARG UV_IMAGE=ghcr.io/astral-sh/uv:0.12.15@sha256:62f8c047d0a0e9ece6b53fc63df902585a67a47a7f318ddec4a37db586edc8e3
ARG DENO_IMAGE=denoland/deno:bin-2.9.6@sha256:4cf0029b9aeeeed5efcbb71828737f0d7c8c8a20072df960e51a5679ef0d21ba

FROM ${UV_IMAGE} AS uv
FROM ${DENO_IMAGE} AS deno
FROM ${PYTHON_IMAGE} AS runtime

ARG FFMPEG_DEBIAN_VERSION=7:5.1.9-0+deb12u1

COPY --from=uv /uv /uvx /usr/local/bin/
COPY --from=deno /deno /usr/local/bin/deno

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        "ffmpeg=${FFMPEG_DEBIAN_VERSION}" \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_NO_DEV=1 \
    DENO_NO_UPDATE_CHECK=1 \
    DENO_NO_PROMPT=1 \
    DENO_DIR=/tmp/deno \
    OPENMEDIA_WORK_DIR=/tmp/openmedia

WORKDIR /app
COPY pyproject.toml uv.lock README.md THIRD_PARTY_NOTICES.md ./
COPY src ./src

# `yt-dlp[default]` installs the pinned yt-dlp-ejs wheel from uv.lock. The application also
# sets yt-dlp remote_components to an empty set, so EJS is bundled and never fetched at run time.
RUN uv sync --locked --no-dev --no-editable --compile-bytecode \
    && /app/.venv/bin/python -c "import yt_dlp_ejs" \
    && deno --version \
    && ffmpeg -version \
    && ffprobe -version \
    && groupadd --gid 10001 openmedia \
    && useradd --uid 10001 --gid 10001 --no-create-home --home-dir /nonexistent openmedia \
    && chown -R 10001:10001 /app \
    && mkdir -p /var/log/openmedia \
    && chown 10001:10001 /var/log/openmedia \
    && chmod 0700 /var/log/openmedia

ENV UV_OFFLINE=1

USER 10001:10001
STOPSIGNAL SIGTERM

HEALTHCHECK --interval=30s --timeout=5s --start-period=120s --retries=3 \
    CMD ["python", "-m", "openmedia", "--healthcheck"]

CMD ["python", "-m", "openmedia"]

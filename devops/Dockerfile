FROM python:3.11-slim

# System dependencies for psycopg2-binary
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Create non-root user
RUN useradd -m -d /home/sunbot sunbot

WORKDIR /home/sunbot/app

# Copy root workspace config
COPY pyproject.toml uv.lock .python-version ./

# Copy all workspace members (needed for uv to resolve workspace deps)
COPY libs/ ./libs/
COPY services/aqi_agent/ ./services/aqi_agent/

# Install the specified package and its workspace dependencies
ARG PACKAGE=aqi-agent
ARG OPTIONAL_BUILD=""
RUN uv sync --package ${PACKAGE} --no-dev --frozen

# Change ownership
RUN chown -R sunbot:sunbot /home/sunbot/app

USER sunbot

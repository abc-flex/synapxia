FROM python:3.15-slim

ARG UV_VERSION=0.5.8

# The installer requires curl (and certificates) to download the release archive
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates

# Download the latest installer
RUN curl -fsSL \
  https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/uv-installer.sh \
  -o /uv-installer.sh \
 && sh /uv-installer.sh

# Run the installer then remove it
RUN sh /uv-installer.sh && rm /uv-installer.sh

# Ensure the installed binary is on the `PATH`
ENV PATH="/root/.local/bin/:$PATH"

# Disable development dependencies
ENV UV_NO_DEV=1

# Copy the project over and install dependencies with uv
WORKDIR /app
COPY . /app

# Sync the project into a new environment, asserting the lockfile is up to date
RUN uv sync --frozen --no-cache


# ---------------------------------------------------------------------------
# agent-borg MCP HTTP Server Docker image
# Builds a production-ready container for Smithery.ai / Railway / Render
# ---------------------------------------------------------------------------

FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency installation
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Copy and install the package in editable mode with all dependencies
COPY pyproject.toml ./
RUN uv pip install --system -e ".[all]" 2>&1 || \
    uv pip install --system -e ".[crypto,embeddings,dev]" 2>&1 || \
    uv pip install --system -e "." 2>&1

# ---------------------------------------------------------------------------
# Production stage
# ---------------------------------------------------------------------------

FROM python:3.12-slim AS production

# Security: run as non-root user
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy the application code
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Environment variables
ENV HOST=0.0.0.0
ENV PORT=8080
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run the HTTP server
# For Railway/Render: use $PORT environment variable if available
CMD ["python", "-m", "borg.integrations.http_server", "--host", "0.0.0.0", "--port", "8080"]

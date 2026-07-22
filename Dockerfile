# ── Stage 1: Build frontend (keeps Node.js out of the runtime image) ──
FROM node:20-slim AS frontend-builder
WORKDIR /build
# vite.config.ts reads ../../VERSION at build time
COPY VERSION /VERSION
COPY web/frontend/package.json web/frontend/package-lock.json ./
RUN npm ci
COPY web/frontend/ ./
RUN npm run build

# ── Stage 2: Runtime ──────────────────────────────────────────────────
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copy source + dependency manifests
COPY pyproject.toml README.md uv.lock VERSION ./
COPY tradingagents/ tradingagents/
COPY cli/ cli/
COPY web/server/ web/server/

# Install Python deps (creates .venv in /app)
RUN pip install uv && uv sync --no-dev

# Copy built frontend dist from builder stage (no Node.js in runtime)
COPY --from=frontend-builder /build/dist web/frontend/dist

# Create non-root user + writable data dir
RUN useradd -r -u 1000 -g root appuser \
    && mkdir -p /data/cache \
    && chown -R appuser:root /app /data

EXPOSE 8000

COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh \
    && chown appuser:root /docker-entrypoint.sh

USER appuser

ENTRYPOINT ["/docker-entrypoint.sh"]

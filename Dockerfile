FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LIVE_MODE=false

# Install minimal system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy configuration and project definitions
COPY pyproject.toml /app/
RUN pip install --no-cache-dir .

# Copy application source
COPY config/ /app/config/
COPY btc5m/ /app/btc5m/
COPY scripts/ /app/scripts/

EXPOSE 9102

ENTRYPOINT ["python"]
CMD ["scripts/run_collector.py"]

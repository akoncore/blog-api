# BASE IMAGE
FROM python:3.12-slim

# METADATA
LABEL maintainer="blog-api"
LABEL description="Blog API with Django, Channels, Celery"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \ 
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies (ДОБАВЛЕН redis-tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gettext \
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

# Create application directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements/base.txt requirements/base.txt
RUN pip install --no-cache-dir -r requirements/base.txt

# Copy project (ИСПРАВЛЕНО НА ОДНУ СТРОКУ)
COPY . .

# Create non-root user
# Create non-root user
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/staticfiles /app/media /app/db && \
    chown -R appuser:appuser /app

# Copy and make entrypoint executable (ВЫПОЛНЯЕМ ДО ПЕРЕКЛЮЧЕНИЯ ПОЛЬЗОВАТЕЛЯ)
COPY --chown=appuser:appuser scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Switch to non-root user
USER appuser

# Entrypoint
ENTRYPOINT ["/entrypoint.sh"]

# Default command (will be overridden in docker-compose)
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "settings.asgi:application"]
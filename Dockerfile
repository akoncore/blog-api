FROM python:3.12-slim

#Metadata
LABEL name="BLog API"
LABEL description="Blog APi with Django,Channels,Redis"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

#Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gettext \
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

# create app
WORKDIR /app

#copy requirements
COPY requirements/base.txt requirements/base.txt
RUN pip install --no-cache-dir -r requirements/base.txt

#copy project
COPY . .

#Create non-root user
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/staticfiles /app/media/ /app/db && \
    chown -R appuser:appuser /app

COPY --chown=appuser:appuser scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh


USER appuser

ENTRYPOINT [ "/entrypoint.sh" ]

CMD [ "daphne","-b","0.0.0.0","-p","8000","settings.asgi:application" ]

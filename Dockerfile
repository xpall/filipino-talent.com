FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends gosu \
    && rm -rf /var/lib/apt/lists/*

ARG APP_UID=1000
ARG APP_GID=1000

RUN groupadd -g "$APP_GID" app \
    && useradd -u "$APP_UID" -g app -M -s /usr/sbin/nologin app

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Build-time placeholders. Real secrets come from .env at runtime.
RUN SECRET_KEY=build-only \
    DEBUG=0 \
    ALLOWED_HOSTS=localhost \
    CSRF_TRUSTED_ORIGINS=http://localhost \
    python manage.py collectstatic --noinput

RUN mkdir -p /app/data && chown -R app:app /app

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]

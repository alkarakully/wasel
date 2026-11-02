FROM python:3.12-slim

# GeoDjango needs GDAL, GEOS and PROJ (gdal-bin pulls in all three).
RUN apt-get update \
    && apt-get install -y --no-install-recommends gdal-bin \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Run as an unprivileged user; static files are collected into a shared volume.
RUN useradd --system --uid 1001 --home /app wasel \
    && mkdir -p /app/staticfiles /app/media \
    && chown wasel /app/staticfiles /app/media
USER wasel

EXPOSE 8000
# Uvicorn serves HTTP and WebSockets (ASGI) with WEB_CONCURRENCY worker
# processes, so every CPU core takes requests: Django runs a process's
# request handlers one at a time, so more processes means more at once.
# --proxy-headers trusts nginx's X-Forwarded-For so logs and throttling see
# the real client address. nginx keeps the access log. (Development keeps `runserver`.)
ENV WEB_CONCURRENCY=8
CMD ["sh", "-c", "exec uvicorn wasel.asgi:application --host 0.0.0.0 --port 8000 --workers \"$WEB_CONCURRENCY\" --proxy-headers --forwarded-allow-ips '*' --timeout-keep-alive 5 --no-server-header --no-access-log"]

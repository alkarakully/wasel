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
# Daphne serves HTTP and WebSockets (ASGI). --proxy-headers trusts nginx's
# X-Forwarded-For so logs and throttling see the real client address.
CMD ["daphne", "--proxy-headers", "--bind", "0.0.0.0", "--port", "8000", "wasel.asgi:application"]

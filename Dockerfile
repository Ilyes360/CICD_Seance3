#
# Multi-stage build (Alpine) + user non-root
#
FROM python:3.12-alpine AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copier d'abord les "manifest(s)" de dépendances pour bénéficier du cache.
# (Sur ce projet Python: c'est `requirements*.txt`, équivalent à `package*.json` côté Node.)
COPY requirements*.txt ./

RUN python -m venv /opt/venv \
    && . /opt/venv/bin/activate \
    && pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt


FROM python:3.12-alpine AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_DEBUG=0

WORKDIR /app

# Créer un user dédié non-root
RUN addgroup -S appgroup \
    && adduser -S appuser -G appgroup \
    && mkdir -p /app \
    && chown -R appuser:appgroup /app

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY . /app
RUN chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

# Par défaut: migrations puis Gunicorn
CMD ["sh", "-c", "python src/manage.py migrate --noinput && gunicorn --chdir /app/src config.wsgi:application --bind 0.0.0.0:8000 --workers 3"]

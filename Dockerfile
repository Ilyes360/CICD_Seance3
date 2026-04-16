FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/

# Par défaut, on désactive le mode debug dans le conteneur.
ENV DJANGO_DEBUG=0

EXPOSE 8000

CMD ["sh", "-c", "python src/manage.py migrate --noinput && gunicorn --chdir /app/src config.wsgi:application --bind 0.0.0.0:8000 --workers 3"]

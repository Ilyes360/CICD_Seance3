import json
import os
import socket
from contextlib import closing

from django.db import connection
from django.http import HttpResponse, JsonResponse


def health(request):
    # Endpoint de healthcheck (DB + cache) pour Docker/K8s.
    db_status = {"status": "down"}
    cache_status = {"status": "down"}

    # Database: tentative d'une requête triviale.
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1;")
            cursor.fetchone()
        db_status = {"status": "up"}
    except Exception as exc:
        db_status = {"status": "down", "error": str(exc)}

    # Cache: ping Redis via une requête RESP minimale (sans dépendance redis-py).
    redis_host = os.getenv("REDIS_HOST", "redis")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    try:
        with closing(socket.create_connection((redis_host, redis_port), timeout=2)) as sock:
            # Commande RESP: "*1\r\n$4\r\nPING\r\n"
            sock.sendall(b"*1\r\n$4\r\nPING\r\n")
            # La réponse attendue commence par "+PONG\r\n"
            data = sock.recv(64)
            if not data.startswith(b"+PONG"):
                raise RuntimeError("Redis ping did not return PONG")
        cache_status = {"status": "up"}
    except Exception as exc:
        cache_status = {"status": "down", "error": str(exc)}

    overall = "ok" if db_status["status"] == "up" and cache_status["status"] == "up" else "error"
    payload = {
        "status": overall,
        "database": db_status,
        "cache": cache_status,
    }

    return JsonResponse(payload)


def healthz(request):
    # Compatibilité rétroactive.
    # (On conserve la même réponse JSON.)
    return health(request)

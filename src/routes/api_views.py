import json

from django.http import HttpResponse, HttpResponseNotAllowed, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from core.models import Task


def _task_to_dict(task):
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "completed": task.completed,
        "created_at": task.created_at.isoformat(),
        "updated_at": task.updated_at.isoformat(),
    }


def _parse_json_body(request):
    try:
        raw_body = request.body.decode("utf-8") if request.body else "{}"
        payload = json.loads(raw_body)
        if not isinstance(payload, dict):
            return None, JsonResponse({"error": "Invalid JSON payload"}, status=400)
        return payload, None
    except json.JSONDecodeError:
        return None, JsonResponse({"error": "Invalid JSON payload"}, status=400)


def _get_task_or_404(task_id):
    try:
        return Task.objects.get(pk=task_id)
    except Task.DoesNotExist:
        return None


def tasks_list(request):
    """
    GET /api/tasks
    Retourne la liste des tâches (triées par date de création décroissante).
    """
    tasks = Task.objects.all().order_by("-created_at")
    return JsonResponse([_task_to_dict(task) for task in tasks], safe=False)


def tasks_create(request):
    """
    POST /api/tasks
    Crée une nouvelle tâche à partir d'un JSON.
    """
    payload, error = _parse_json_body(request)
    if error:
        return error

    title = (payload.get("title") or "").strip()
    if not title:
        return JsonResponse({"error": "title is required"}, status=400)

    task = Task.objects.create(
        title=title,
        description=payload.get("description", ""),
        completed=bool(payload.get("completed", False)),
    )
    return JsonResponse(_task_to_dict(task), status=201)


def task_get(request, task_id):
    """
    GET /api/tasks/<id>
    Retourne une tâche.
    """
    task = _get_task_or_404(task_id)
    if task is None:
        return JsonResponse({"error": "Task not found"}, status=404)
    return JsonResponse(_task_to_dict(task))


def task_put(request, task_id):
    """
    PUT /api/tasks/<id>
    Met à jour une tâche à partir d'un JSON.
    """
    task = _get_task_or_404(task_id)
    if task is None:
        return JsonResponse({"error": "Task not found"}, status=404)

    payload, error = _parse_json_body(request)
    if error:
        return error

    if "title" in payload:
        title = (payload.get("title") or "").strip()
        if not title:
            return JsonResponse({"error": "title cannot be empty"}, status=400)
        task.title = title

    if "description" in payload:
        task.description = payload.get("description") or ""

    if "completed" in payload:
        task.completed = bool(payload.get("completed"))

    task.save()
    return JsonResponse(_task_to_dict(task))


def task_delete(request, task_id):
    """
    DELETE /api/tasks/<id>
    Supprime une tâche.
    """
    task = _get_task_or_404(task_id)
    if task is None:
        return JsonResponse({"error": "Task not found"}, status=404)
    task.delete()
    return HttpResponse(status=204)


@csrf_exempt
def tasks_collection(request):
    handlers = {"GET": tasks_list, "POST": tasks_create}
    handler = handlers.get(request.method)
    if handler is None:
        return HttpResponseNotAllowed(["GET", "POST"])
    return handler(request)


@csrf_exempt
def tasks_detail(request, task_id):
    handlers = {"GET": task_get, "PUT": task_put, "DELETE": task_delete}
    handler = handlers.get(request.method)
    if handler is None:
        return HttpResponseNotAllowed(["GET", "PUT", "DELETE"])
    return handler(request, task_id)


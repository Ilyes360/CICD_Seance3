from django.urls import path

from core.views import health, healthz

from .api_views import tasks_collection, tasks_detail

urlpatterns = [
    # Health checks (smoke test)
    path("health", health),
    path("health/", health),
    path("healthz/", healthz),
    # Tasks CRUD
    path("api/tasks", tasks_collection),
    path("api/tasks/", tasks_collection),
    path("api/tasks/<int:task_id>", tasks_detail),
    path("api/tasks/<int:task_id>/", tasks_detail),
]

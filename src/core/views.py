from django.http import HttpResponse


def health(request):
    # Endpoint de smoke test pour vérifier que Django répond.
    return HttpResponse("ok")


def healthz(request):
    # Compatibilité rétroactive.
    return health(request)

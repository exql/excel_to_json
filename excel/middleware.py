from django.shortcuts import redirect
from django.urls import reverse, NoReverseMatch
from django.conf import settings

class RestrictLaboratorioMiddleware:
    """
    🚀 Middleware que bloquea el acceso a ciertas vistas si el usuario pertenece al grupo 'laboratorio'.
    ✅ La lista de vistas restringidas puede modificarse en settings.py (RESTRICTED_VIEWS).
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # ⚡ Verifica si el usuario está autenticado antes de acceder a sus grupos
        if hasattr(request, "user") and request.user.is_authenticated:
            if request.user.groups.filter(name="laboratorio").exists():  # ✅ Ahora coincide con Django Admin

                restricted_urls = []
                for view in settings.RESTRICTED_VIEWS:
                    try:
                        restricted_urls.append(reverse(view))  # ✅ Intenta generar la URL
                    except NoReverseMatch:
                        pass  # ✅ Ignora vistas que requieren argumentos

                # 📌 Si el usuario intenta acceder a una vista restringida, lo redirigimos al índice
                if request.path in restricted_urls:
                    return redirect("index")  # ✅ Redirige a la página de inicio

        return self.get_response(request)
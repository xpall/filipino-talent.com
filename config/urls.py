from django.conf import settings
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("", include("core.urls")),
    path("", include("registry.urls")),
    path("accounts/", include("allauth.urls")),
    path("admin/", RedirectView.as_view(url="/dashboard", permanent=False)),
]

handler404 = "core.views.not_found"
handler500 = "core.views.server_error"

if settings.DEBUG:
    from django.conf.urls.static import static

    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

"""URL routes for the Clipboard Sync backend."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("clipboard.urls")),
]

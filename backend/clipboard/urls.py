from django.urls import path

from clipboard.views import ClipboardEntryCreateView, LatestClipboardEntryView

urlpatterns = [
    path("clipboard/", ClipboardEntryCreateView.as_view(), name="clipboard-create"),
    path("clipboard/latest/", LatestClipboardEntryView.as_view(), name="clipboard-latest"),
]

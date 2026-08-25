from django.urls import path

from clipboard.views import (
    ClipboardEntryCreateView,
    DevicePairView,
    LatestClipboardEntryView,
    PairingCodeCreateView,
)

urlpatterns = [
    path("clipboard/", ClipboardEntryCreateView.as_view(), name="clipboard-create"),
    path("clipboard/latest/", LatestClipboardEntryView.as_view(), name="clipboard-latest"),
    path("device/pairing/create/", PairingCodeCreateView.as_view(), name="pairing-create"),
    path("device/pair/", DevicePairView.as_view(), name="device-pair"),
]

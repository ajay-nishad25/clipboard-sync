from django.urls import path

from clipboard.views import (
    ClipboardEntryCreateView,
    DeviceCredentialRegisterView,
    DevicePairView,
    DeviceUnpairView,
    LatestClipboardEntryView,
    PairingCodeCreateView,
)

urlpatterns = [
    path("clipboard/", ClipboardEntryCreateView.as_view(), name="clipboard-create"),
    path("clipboard/latest/", LatestClipboardEntryView.as_view(), name="clipboard-latest"),
    path("device/credential/register/", DeviceCredentialRegisterView.as_view(), name="credential-register"),
    path("device/unpair/", DeviceUnpairView.as_view(), name="device-unpair"),
    path("device/pairing/create/", PairingCodeCreateView.as_view(), name="pairing-create"),
    path("device/pair/", DevicePairView.as_view(), name="device-pair"),
]

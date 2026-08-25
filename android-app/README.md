# Android Clipboard Sync App

Phase 6 Java Android application that implements **Manual Android Clipboard Synchronization**
compatible with Android 10+ / Android 14 restrictions.

## Architecture

```text
                                 ANDROID APP
                                      │
           ┌──────────────────────────┴──────────────────────────┐
           │                                                     │
           ▼                                                     ▼
    [SEND CLIPBOARD]                                     [RECEIVE CLIPBOARD]
           │                                                     │
           ▼                                                     ▼
 cm.getPrimaryClip()                                GET /api/clipboard/latest/
 (MainActivity Focused)                                          │
           │                                                     ▼
           ▼                                            HTTP JSON Response
ClipboardWebSocketClient                                         │
 (ws://127.0.0.1:8000)                                           ▼
           │                                            cm.setPrimaryClip()
           ▼ (clipboard.update)                                  │
    Django Backend                                               ▼
           │                                             Android Clipboard
           ▼ (clipboard.ack)
 "Clipboard sent successfully"
```

## Build & Test

```powershell
cd android-app
# Run unit tests
.\gradlew.bat test

# Build debug APK
.\gradlew.bat assembleDebug
```

The APK is placed at: `app/build.gradle` → `app/build/outputs/apk/debug/app-debug.apk`

## Physical Device Setup (USB Debugging)

1. Connect your physical Android device (e.g. Realme Android 14) via USB with USB Debugging enabled.
2. Enable port forwarding:
   ```powershell
   adb reverse tcp:8000 tcp:8000
   ```
3. Install the debug APK:
   ```powershell
   .\gradlew.bat installDebug
   ```

## User Workflows

### 1. SEND CLIPBOARD
1. Open **Clipboard Sync** app on Android → tap **START** to establish WebSocket connection.
2. Copy any text in Chrome, WhatsApp, Notes, etc.
3. Return to **Clipboard Sync** app.
4. Tap **`SEND CLIPBOARD`**.
5. `MainActivity` reads the clipboard while focused, dispatches text over WebSocket (`clipboard.update`), waits for `clipboard.ack` from Django, and displays:
   `"Clipboard sent successfully"`

### 2. RECEIVE CLIPBOARD
1. Ensure desktop agent has sent text to Django (or an entry exists in backend DB).
2. Open **Clipboard Sync** app on Android.
3. Tap **`RECEIVE CLIPBOARD`**.
4. Android fetches the latest entry via `GET http://127.0.0.1:8000/api/clipboard/latest/`, writes it to Android clipboard using `setPrimaryClip()`, and displays:
   `"Clipboard received successfully"`
5. Paste into any Android application.

## Permissions

| Permission | Purpose |
|---|---|
| `INTERNET` | WebSocket connection & REST HTTP requests to Django backend |
| `FOREGROUND_SERVICE` | Maintain background WebSocket connection |
| `FOREGROUND_SERVICE_DATA_SYNC` | API 34+: foreground service type for data sync |
| `POST_NOTIFICATIONS` | API 33+: show service notification |

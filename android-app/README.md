# Android Clipboard Sync App

Phase 6 Java Android application that monitors the Android clipboard and
forwards each new text value to the Django backend using the Phase 5
`clipboard.update` WebSocket protocol.

## Data flow

```text
Android Clipboard
       ↓  (ClipboardManager.OnPrimaryClipChangedListener)
ClipboardMonitorService (Foreground Service)
       ↓  (OkHttp WebSocket — clipboard.update)
Django Backend — ws://10.0.2.2:8000/ws/clipboard/
       ↓
ClipboardEntry / SQLite
       ↓  (clipboard.ack)
Android (logged in Logcat)
```

## Prerequisites

- Android Studio (any recent version)
- Android device or emulator running API 26 (Android 8.0) or higher
- Django backend running (see `backend/README.md`)

## Build requirements

| Component | Version |
|-----------|---------|
| Android Gradle Plugin | 9.0.0 |
| Gradle wrapper | 9.1.0 (downloaded automatically) |
| compileSdk / targetSdk | 37 (Android 17) |
| minSdk | 26 (Android 8.0) |
| Build tools | 36.0.0 |
| Java source / target | 17 |

## Build

```powershell
cd android-app
.\gradlew.bat assembleDebug
```

The APK is placed at: `app/build/outputs/apk/debug/app-debug.apk`

## Install on a device

```powershell
# Install (device must be connected via USB or emulator must be running)
.\gradlew.bat installDebug
```

## Android Emulator (AVD) setup

The backend runs on your Windows machine. The Android emulator cannot reach
`127.0.0.1`; it uses `10.0.2.2` instead.

The app is pre-configured to connect to `ws://10.0.2.2:8000/ws/clipboard/`.
No changes are needed for the emulator.

**Start the emulator, then start the Django server, then tap Start in the app.**

## Physical device setup

**Option A — same WiFi network**

1. Find your Windows machine's local IP address: `ipconfig` (look for IPv4 address, e.g. `192.168.1.50`).
2. Edit `Config.java` and change `WS_BASE_URL` to your machine's IP:
   ```java
   public static final String WS_BASE_URL = "ws://192.168.1.50:8000/ws/clipboard/";
   ```
3. Also add your IP to `res/xml/network_security_config.xml`:
   ```xml
   <domain includeSubdomains="false">192.168.1.50</domain>
   ```
4. Rebuild: `.\gradlew.bat assembleDebug`

**Option B — USB debugging with port forwarding**

```powershell
adb reverse tcp:8000 tcp:8000
```

Then change `WS_BASE_URL` to `ws://127.0.0.1:8000/ws/clipboard/`.

## Permissions

| Permission | Purpose |
|---|---|
| `INTERNET` | WebSocket connection to Django backend |
| `FOREGROUND_SERVICE` | Start the clipboard monitor as a foreground service |
| `FOREGROUND_SERVICE_DATA_SYNC` | API 34+: foreground service type for data transfer |
| `POST_NOTIFICATIONS` | API 33+: show the foreground service notification |

The app requests `POST_NOTIFICATIONS` at runtime on API 33+. Notification
permission is required for the foreground service to run on Android 13+.

## Android clipboard access restriction

On Android 10 and above, apps cannot read clipboard data unless they hold the
focused window. This affects clipboard sync when the app is in the background.

| Scenario | Result |
|---|---|
| App open and visible | Clipboard sync works reliably |
| App in background (API < 29) | Clipboard sync works reliably |
| App in background (API 29+) | Clipboard read returns null; value is dropped |

**For reliable testing:** keep the app visible on screen, or use an emulator
running API 26–28 for full background sync.

## Manual integration test

1. Start the Django backend:
   ```powershell
   cd backend
   .\.venv\Scripts\Activate.ps1
   python manage.py runserver
   ```
2. Start the Android emulator and install the app.
3. Open the app → tap **Start**.
4. Confirm the status shows "Connected — monitoring clipboard."
5. Copy any text on the emulator (long-press in a text field → Copy).
6. Observe the status update in the app and the `clipboard.ack` in Logcat.
7. Verify the entry was stored:
   ```powershell
   Invoke-RestMethod -Uri http://127.0.0.1:8000/api/clipboard/latest/
   ```
   The response should contain the copied text and `device_id: "android-001"`.

## Failure/recovery test

1. Start the app (service running, WebSocket connected).
2. Stop Django. Confirm the app shows "Disconnected — reconnecting…"
3. Restart Django. Confirm the app automatically reconnects (2 → 5 → 15 → 30 s backoff).
4. Copy text. Confirm sync after reconnect.

## Known limitations (Phase 6)

- No server-side broadcasting: clipboard values sent from Android are stored
  but not forwarded to the desktop agent.
- Clipboard sync from background may fail on Android 10+ (see above).
- No authentication or device authorization.
- WebSocket URL and device ID are hardcoded constants in `Config.java`.
- No emulator/physical device auto-detection.

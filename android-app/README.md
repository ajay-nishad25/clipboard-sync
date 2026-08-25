# Android Clipboard Sync App

Java Android application implementing **Manual Android Clipboard Synchronization** compatible with Android 10+ / Android 14 (API 34) restrictions.

---

## Current Verified Baseline (Phases 1–8)

### Architecture Diagram
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

### Build & Test
```powershell
cd android-app
.\gradlew.bat test            # Run unit tests (ClipboardApiClientTest, ConfigTest)
.\gradlew.bat assembleDebug   # Build debug APK
```

### Physical Device USB Setup
```powershell
adb reverse tcp:8000 tcp:8000
.\gradlew.bat installDebug
```

---

## Mandatory Architectural Rules (MUST NOT BE CHANGED)

1. **Manual Clipboard Workflows Only**:
   - `[ SEND CLIPBOARD ]`: Reads system clipboard in user-focused `MainActivity` and sends over WebSocket.
   - `[ RECEIVE CLIPBOARD ]`: Fetches latest entry via HTTP REST (`GET /api/clipboard/latest/`) and applies to Android clipboard via `setPrimaryClip()`.
2. **No Background Clipboard Harvesting**:
   - `ClipboardMonitorService` manages background WebSocket lifecycle only.
   - It does **not** call `getPrimaryClip()` while running in the background, in compliance with Android 10+ privacy restrictions.

---

## Persistent Device ID

- Auto-generates a persistent device UUID (`android-<uuid>`) saved in Android `SharedPreferences` (`clipboard_sync_prefs`).
- Reused across app restarts; reset only upon app re-install or clear data.

---

## Phase 9 Android Roadmap (PLANNED / NEXT)

Phase 9 adds device pairing and user authentication to the Android application:

1. **Pairing Screen UI**:
   - User inputs the pairing code displayed by Desktop Agent (e.g. `AB7K-29XM`).
   - Taps **`[ PAIR DEVICE ]`**.
2. **Device Enrollment**:
   - App calls `POST /api/device/pair/` with pairing code and device ID.
   - Backend returns user association and persistent device token.
   - Device token saved securely in Android `SharedPreferences`.
3. **Authenticated Communication**:
   - WebSocket connection includes device token (`wss://api.example.com/ws/clipboard/?token=<device_token>`).
   - `[ RECEIVE CLIPBOARD ]` sends `Authorization: Bearer <device_token>` header.
4. **Data Isolation Guarantee**:
   - Android A sends/receives clipboard data restricted strictly to User A's channel scope (`clipboard_user_A`).

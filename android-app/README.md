# Android Clipboard Sync App

Java Android application implementing **Manual Android Clipboard Synchronization** and **Desktop Device Pairing** with **Authenticated Device Credentials** compatible with Android 10+ / Android 14 (API 34) restrictions.

---

## Current Verified Baseline (Phases 1–9C Implemented)

### Architecture Diagram
```text
                                 ANDROID APP
                                      │
           ┌──────────────────────────┼──────────────────────────┐
           │                          │                          │
           ▼                          ▼                          ▼
     [ PAIR DEVICE ]          [SEND CLIPBOARD]           [RECEIVE CLIPBOARD]
           │                          │                          │
           ▼                          ▼                          ▼
  POST /api/device/pair/     cm.getPrimaryClip()        GET /api/clipboard/latest/
  (Code: AB7K-29XM)          (MainActivity Focused)     Header: Bearer <device_token>
           │                          │                          │
           ▼                          ▼                          ▼
  Receives device_token     ClipboardWebSocketClient    HTTP JSON Response
  SharedPreferences saved     (?token=<device_token>)             │
                              (clipboard.update)                 ▼
                                                         cm.setPrimaryClip()
```

### Build & Test
```powershell
cd android-app
.\gradlew.bat test            # Run unit tests (ClipboardApiClientTest, ConfigTest) - 12 tests
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
   - `[ SEND CLIPBOARD ]`: Reads system clipboard in user-focused `MainActivity` and sends over authenticated WebSocket (`?token=<device_token>`).
   - `[ RECEIVE CLIPBOARD ]`: Fetches latest entry via HTTP REST (`GET /api/clipboard/latest/` with `Authorization: Bearer <device_token>`) and applies to Android clipboard via `setPrimaryClip()`.
2. **Desktop Device Pairing UI & Credential Persistence**:
   - Enter 8-character pairing code (e.g. `AB7K-29XM`) and tap `[ PAIR DEVICE ]`.
   - Calls `POST /api/device/pair/` to associate Android Device ID with Desktop's owner User account and obtain issued `device_token` secret.
   - Stores pairing state and `device_token` in `SharedPreferences`.
3. **No Background Clipboard Harvesting**:
   - `ClipboardMonitorService` manages background WebSocket lifecycle only.
   - It does **not** call `getPrimaryClip()` while running in the background, in compliance with Android 10+ privacy restrictions.

---

## Persistent Device ID & Token

- Auto-generates a persistent device UUID (`android-<uuid>`) and stores issued `device_token` secret in Android `SharedPreferences` (`clipboard_sync_prefs`).
- Reused across app restarts; reset only upon app re-install or explicit unpair.

---

## Phase 9 Remaining Roadmap (PLANNED / NEXT)

- **Phase 9D**: Configurable production transport endpoints (`https://` and `wss://`).
- **Phase 9E**: Deployment hardening.

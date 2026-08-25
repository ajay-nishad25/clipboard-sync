# Android Clipboard Sync App

Java Android application implementing **Manual Android Clipboard Synchronization** and **Desktop Device Pairing** compatible with Android 10+ / Android 14 (API 34) restrictions.

---

## Current Verified Baseline (Phases 1–9B Implemented)

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
  POST /api/device/pair/     cm.getPrimaryClip()        GET /api/clipboard/latest/?device_id=...
  (Code: AB7K-29XM)          (MainActivity Focused)                  │
           │                          │                          ▼
           ▼                          ▼                 HTTP JSON Response
  Paired with User A        ClipboardWebSocketClient                 │
  SharedPreferences saved     (ws://127.0.0.1:8000)                   ▼
                              (clipboard.update)         cm.setPrimaryClip()
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
   - `[ SEND CLIPBOARD ]`: Reads system clipboard in user-focused `MainActivity` and sends over WebSocket.
   - `[ RECEIVE CLIPBOARD ]`: Fetches latest entry via HTTP REST (`GET /api/clipboard/latest/?device_id=...`) and applies to Android clipboard via `setPrimaryClip()`.
2. **Desktop Device Pairing UI**:
   - Section in `MainActivity`: Enter 8-character pairing code (e.g. `AB7K-29XM`) and tap `[ PAIR DEVICE ]`.
   - Calls `POST /api/device/pair/` to associate Android Device ID with Desktop's owner User account.
   - Stores pairing state in `SharedPreferences`.
3. **No Background Clipboard Harvesting**:
   - `ClipboardMonitorService` manages background WebSocket lifecycle only.
   - It does **not** call `getPrimaryClip()` while running in the background, in compliance with Android 10+ privacy restrictions.

---

## Persistent Device ID & Pairing State

- Auto-generates a persistent device UUID (`android-<uuid>`) saved in Android `SharedPreferences` (`clipboard_sync_prefs`).
- Reused across app restarts; reset only upon app re-install or clear data.

---

## Phase 9 Remaining Roadmap (PLANNED / NEXT)

- **Phase 9C**: Persistent Device Tokens and Authenticated Transport (`wss://` and Bearer REST headers).

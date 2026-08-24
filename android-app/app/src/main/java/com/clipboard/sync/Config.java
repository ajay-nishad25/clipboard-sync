package com.clipboard.sync;

/**
 * Application-wide constants for Clipboard Sync.
 *
 * All values are development defaults. Adjust WS_BASE_URL and DEVICE_ID
 * as needed for your environment before running.
 */
public final class Config {

    /**
     * WebSocket base URL for the Django backend.
     *
     * Environment     | Address
     * ----------------+------------------------------------------------------
     * Android Emulator| ws://10.0.2.2:8000/ws/clipboard/
     *                 | 10.0.2.2 is the emulator's alias for the host loopback.
     * Physical device | ws://<host-local-ip>:8000/ws/clipboard/
     * (same WiFi)     | Find the host IP with `ipconfig` on Windows.
     * Physical device | ws://127.0.0.1:8000/ws/clipboard/
     * (USB, adb rev.) | Run: adb reverse tcp:8000 tcp:8000
     */
    public static final String WS_BASE_URL = "ws://127.0.0.1:8000/ws/clipboard/";

    /** REST API endpoint to retrieve the most recent clipboard entry. */
    public static final String REST_LATEST_URL = "http://127.0.0.1:8000/api/clipboard/latest/";

    /** Development device identifier sent with every clipboard.update message. */
    public static final String DEVICE_ID = "android-001";

    /** Notification channel ID for the foreground service. */
    public static final String NOTIFICATION_CHANNEL_ID = "clipboard_sync_channel";

    /** Foreground service notification ID. */
    public static final int NOTIFICATION_ID = 1;

    private Config() {}
}

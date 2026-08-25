package com.clipboard.sync;

import android.content.Context;
import android.content.SharedPreferences;

import java.util.UUID;

/**
 * Application-wide constants and persistent configuration for Clipboard Sync.
 */
public final class Config {

    public static final String WS_BASE_URL = "ws://127.0.0.1:8000/ws/clipboard/";
    public static final String REST_LATEST_URL = "http://127.0.0.1:8000/api/clipboard/latest/";
    public static final String PAIRING_URL = "http://127.0.0.1:8000/api/device/pair/";
    public static final String DEVICE_ID = "android-001";

    public static final String NOTIFICATION_CHANNEL_ID = "clipboard_sync_channel";
    public static final int NOTIFICATION_ID = 1;

    private static final String PREFS_NAME = "clipboard_sync_prefs";
    private static final String KEY_DEVICE_ID = "device_id";
    private static final String KEY_IS_PAIRED = "is_paired";

    private Config() {}

    /**
     * Get or generate a persistent device identifier stored in SharedPreferences.
     *
     * @param context Application or Activity context.
     * @return Persistent device ID string.
     */
    public static synchronized String getDeviceId(Context context) {
        if (context == null) {
            return DEVICE_ID;
        }
        SharedPreferences prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        String deviceId = prefs.getString(KEY_DEVICE_ID, null);
        if (deviceId == null || deviceId.trim().isEmpty()) {
            deviceId = "android-" + UUID.randomUUID().toString().substring(0, 8);
            prefs.edit().putString(KEY_DEVICE_ID, deviceId).apply();
        }
        return deviceId;
    }

    /**
     * Check if this Android device is paired with a desktop account.
     */
    public static synchronized boolean isPaired(Context context) {
        if (context == null) return false;
        SharedPreferences prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        return prefs.getBoolean(KEY_IS_PAIRED, false);
    }

    /**
     * Set the local device pairing state.
     */
    public static synchronized void setPaired(Context context, boolean paired) {
        if (context == null) return;
        SharedPreferences prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        prefs.edit().putBoolean(KEY_IS_PAIRED, paired).apply();
    }
}

package com.clipboard.sync;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ServiceInfo;
import android.os.Build;
import android.os.IBinder;
import android.util.Log;

import androidx.annotation.Nullable;
import androidx.core.app.NotificationCompat;

import com.clipboard.sync.websocket.ClipboardWebSocketClient;

/**
 * Foreground service that monitors the Android clipboard and forwards new
 * text values to the Django backend using the Phase 5 clipboard.update
 * WebSocket protocol.
 *
 * Android clipboard access restriction (API 29+):
 * On Android 10 and above, apps cannot read clipboard data while in the
 * background unless they hold the focused window. A foreground service has
 * a persistent notification but no focused window, so getPrimaryClip() may
 * return null when the user copies text while our Activity is not visible.
 *
 * Reliable behaviour:
 * - Android < 10 (API 26–28): clipboard read always succeeds.
 * - Android 10+ with Activity visible: clipboard read succeeds because the
 *   app is in focus; the listener in MainActivity delegates to this service.
 * - Android 10+ with Activity not visible: clipboard read from service may
 *   return null; the failure is logged and the value is dropped.
 *
 * This is a known Android privacy restriction and is documented in
 * android-app/README.md as a Phase 6 limitation.
 */
public class ClipboardMonitorService extends Service {

    private static final String TAG = "ClipboardMonitorSvc";

    /** Broadcast action for status updates sent to MainActivity. */
    public static final String ACTION_STATUS_UPDATE = "com.clipboard.sync.STATUS_UPDATE";
    public static final String EXTRA_STATUS_MESSAGE = "status_message";
    public static final String EXTRA_LAST_CONTENT  = "last_content";
    public static final String EXTRA_SYNC_COUNT    = "sync_count";

    private ClipboardManager clipboardManager;
    private ClipboardManager.OnPrimaryClipChangedListener clipboardListener;
    private ClipboardWebSocketClient wsClient;

    private String lastSentContent = null;
    private int syncCount = 0;

    // ------------------------------------------------------------------
    // Service lifecycle
    // ------------------------------------------------------------------

    @Override
    public void onCreate() {
        super.onCreate();
        createNotificationChannel();
        startForegroundWithType(buildNotification(getString(R.string.notif_starting)));
        initWebSocket();
        initClipboardMonitor();
        Log.i(TAG, "ClipboardMonitorService started.");
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        // START_STICKY: if the process is killed, Android restarts the service
        // (without an intent), which re-establishes the clipboard listener and
        // WebSocket connection.
        return START_STICKY;
    }

    @Nullable
    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    @Override
    public void onDestroy() {
        if (clipboardManager != null && clipboardListener != null) {
            clipboardManager.removePrimaryClipChangedListener(clipboardListener);
        }
        if (wsClient != null) {
            wsClient.close();
        }
        Log.i(TAG, "ClipboardMonitorService stopped.");
        super.onDestroy();
    }

    // ------------------------------------------------------------------
    // WebSocket initialisation
    // ------------------------------------------------------------------

    private void initWebSocket() {
        wsClient = new ClipboardWebSocketClient(
                Config.WS_BASE_URL,
                Config.DEVICE_ID,
                new ClipboardWebSocketClient.StatusListener() {

                    @Override
                    public void onConnected() {
                        updateNotification(getString(R.string.notif_connected));
                        broadcastStatus(getString(R.string.status_connected), null);
                    }

                    @Override
                    public void onDisconnected() {
                        updateNotification(getString(R.string.notif_reconnecting));
                        broadcastStatus(getString(R.string.status_reconnecting), null);
                    }

                    @Override
                    public void onAckReceived(String deviceId, String status) {
                        syncCount++;
                        Log.i(TAG, "Ack from server: device=" + deviceId
                                + " status=" + status + " total=" + syncCount);
                        broadcastStatus(
                                getString(R.string.status_synced, syncCount),
                                lastSentContent
                        );
                    }

                    @Override
                    public void onError(String code, String detail) {
                        Log.w(TAG, "Server error: " + code + " — " + detail);
                        broadcastStatus(getString(R.string.status_server_error, code), null);
                    }
                });
        wsClient.connect();
    }

    // ------------------------------------------------------------------
    // Clipboard monitoring
    // ------------------------------------------------------------------

    private void initClipboardMonitor() {
        clipboardManager = (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
        if (clipboardManager == null) {
            Log.e(TAG, "ClipboardManager is unavailable on this device.");
            return;
        }
        clipboardListener = this::onClipboardChanged;
        clipboardManager.addPrimaryClipChangedListener(clipboardListener);
        Log.i(TAG, "Clipboard listener registered.");
    }

    /**
     * Called by the OS whenever the primary clipboard changes.
     *
     * On Android 10+ (API 29+), getPrimaryClip() returns null when the app
     * does not hold the focused window. The failure is logged and the value
     * is silently dropped; monitoring continues for the next change.
     */
    private void onClipboardChanged() {
        if (clipboardManager == null) return;

        ClipData clip;
        try {
            clip = clipboardManager.getPrimaryClip();
        } catch (SecurityException e) {
            // Thrown on some Android 12+ builds when the app is strictly
            // in the background without a focused window.
            Log.w(TAG, "Clipboard read denied by the OS (API 29+ background restriction).");
            return;
        }

        if (clip == null || clip.getItemCount() == 0) {
            Log.d(TAG, "Clipboard is empty or inaccessible from the background.");
            return;
        }

        CharSequence raw = clip.getItemAt(0).getText();
        if (raw == null) {
            Log.d(TAG, "Clipboard text is null — likely restricted on this Android version.");
            return;
        }

        String content = raw.toString();
        if (content.isEmpty()) {
            Log.d(TAG, "Clipboard text is empty; ignoring.");
            return;
        }

        // Duplicate prevention: skip if this value was already sent.
        if (content.equals(lastSentContent)) {
            Log.d(TAG, "Duplicate clipboard value; skipping.");
            return;
        }

        Log.i(TAG, "New clipboard value (" + content.length() + " chars); sending.");
        lastSentContent = content;

        if (wsClient != null && wsClient.isConnected()) {
            wsClient.send(content);
        } else {
            Log.w(TAG, "WebSocket not connected — clipboard value dropped.");
            broadcastStatus(getString(R.string.status_not_connected), null);
        }
    }

    // ------------------------------------------------------------------
    // Notification helpers
    // ------------------------------------------------------------------

    private void createNotificationChannel() {
        NotificationChannel channel = new NotificationChannel(
                Config.NOTIFICATION_CHANNEL_ID,
                getString(R.string.app_name),
                NotificationManager.IMPORTANCE_LOW
        );
        channel.setDescription(getString(R.string.notif_channel_description));
        NotificationManager mgr = getSystemService(NotificationManager.class);
        if (mgr != null) mgr.createNotificationChannel(channel);
    }

    private void startForegroundWithType(Notification notification) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            // API 29+: pass the foreground service type declared in the manifest.
            startForeground(
                    Config.NOTIFICATION_ID,
                    notification,
                    ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC
            );
        } else {
            startForeground(Config.NOTIFICATION_ID, notification);
        }
    }

    private void updateNotification(String text) {
        NotificationManager mgr = getSystemService(NotificationManager.class);
        if (mgr != null) mgr.notify(Config.NOTIFICATION_ID, buildNotification(text));
    }

    private Notification buildNotification(String contentText) {
        PendingIntent pi = PendingIntent.getActivity(
                this, 0,
                new Intent(this, MainActivity.class),
                PendingIntent.FLAG_IMMUTABLE
        );
        return new NotificationCompat.Builder(this, Config.NOTIFICATION_CHANNEL_ID)
                .setContentTitle(getString(R.string.app_name))
                .setContentText(contentText)
                .setSmallIcon(android.R.drawable.ic_menu_share)
                .setContentIntent(pi)
                .setOngoing(true)
                .setPriority(NotificationCompat.PRIORITY_LOW)
                .build();
    }

    // ------------------------------------------------------------------
    // IPC: status broadcast to MainActivity
    // ------------------------------------------------------------------

    /**
     * Broadcast a status update so MainActivity can refresh the UI.
     *
     * @param message  Human-readable status string.
     * @param content  The clipboard content just synced, or null.
     */
    private void broadcastStatus(String message, @Nullable String content) {
        Intent intent = new Intent(ACTION_STATUS_UPDATE);
        intent.putExtra(EXTRA_STATUS_MESSAGE, message);
        intent.putExtra(EXTRA_SYNC_COUNT, syncCount);
        if (content != null) intent.putExtra(EXTRA_LAST_CONTENT, content);
        sendBroadcast(intent);
    }
}

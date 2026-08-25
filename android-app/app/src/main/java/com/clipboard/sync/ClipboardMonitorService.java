package com.clipboard.sync;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
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
    public static final String EXTRA_IS_ACK        = "is_ack";
    public static final String EXTRA_IS_SUCCESS    = "is_success";

    /** Command action for MainActivity to trigger text sync. */
    public static final String ACTION_SEND_CLIPBOARD = "com.clipboard.sync.SEND_CLIPBOARD";
    public static final String EXTRA_CLIPBOARD_TEXT = "clipboard_text";

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
        Log.i(TAG, "ClipboardMonitorService started.");
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent != null && ACTION_SEND_CLIPBOARD.equals(intent.getAction())) {
            String text = intent.getStringExtra(EXTRA_CLIPBOARD_TEXT);
            if (text != null && !text.isEmpty()) {
                sendClipboardText(text);
            }
        }
        // START_STICKY: if the process is killed, Android restarts the service
        // and re-establishes the WebSocket connection.
        return START_STICKY;
    }

    @Nullable
    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    @Override
    public void onDestroy() {
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
                Config.getDeviceId(this),
                new ClipboardWebSocketClient.StatusListener() {

                    @Override
                    public void onConnected() {
                        updateNotification(getString(R.string.notif_connected));
                        broadcastStatus(getString(R.string.status_connected), null, false, false);
                    }

                    @Override
                    public void onDisconnected() {
                        updateNotification(getString(R.string.notif_reconnecting));
                        broadcastStatus(getString(R.string.status_reconnecting), null, false, false);
                    }

                    @Override
                    public void onAckReceived(String deviceId, String status) {
                        syncCount++;
                        Log.i(TAG, "Ack from server: device=" + deviceId
                                + " status=" + status + " total=" + syncCount);
                        broadcastStatus(
                                getString(R.string.status_sent_success),
                                lastSentContent,
                                true,
                                true
                        );
                    }

                    @Override
                    public void onError(String code, String detail) {
                        Log.w(TAG, "Server error: " + code + " — " + detail);
                        broadcastStatus(getString(R.string.status_send_failed), null, true, false);
                    }
                });
        wsClient.connect();
    }

    /**
     * Send clipboard text to the Django WebSocket server.
     *
     * @param content Plain text clipboard string.
     */
    public void sendClipboardText(String content) {
        if (content == null || content.isEmpty()) {
            return;
        }

        Log.i(TAG, "Sending clipboard value (" + content.length() + " chars).");
        lastSentContent = content;

        if (wsClient != null && wsClient.isConnected()) {
            boolean enqueued = wsClient.send(content);
            if (!enqueued) {
                Log.w(TAG, "WebSocket send buffer full — send failed.");
                broadcastStatus(getString(R.string.status_send_failed), null, true, false);
            }
        } else {
            Log.w(TAG, "WebSocket not connected — clipboard value dropped.");
            broadcastStatus(getString(R.string.status_send_failed), null, true, false);
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
        Intent openIntent = new Intent(this, MainActivity.class);
        PendingIntent pi = PendingIntent.getActivity(
                this, 0,
                openIntent,
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
     * @param message    Human-readable status string.
     * @param content    The clipboard content just synced, or null.
     * @param isAck      True if this broadcast is in response to a send request.
     * @param isSuccess  True if the send operation succeeded.
     */
    private void broadcastStatus(String message, @Nullable String content, boolean isAck, boolean isSuccess) {
        Intent intent = new Intent(ACTION_STATUS_UPDATE);
        intent.setPackage(getPackageName());
        intent.putExtra(EXTRA_STATUS_MESSAGE, message);
        intent.putExtra(EXTRA_SYNC_COUNT, syncCount);
        intent.putExtra(EXTRA_IS_ACK, isAck);
        intent.putExtra(EXTRA_IS_SUCCESS, isSuccess);
        if (content != null) intent.putExtra(EXTRA_LAST_CONTENT, content);
        sendBroadcast(intent);
    }
}

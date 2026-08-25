package com.clipboard.sync.websocket;

import android.util.Log;

import org.json.JSONException;
import org.json.JSONObject;

import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicReference;

import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.Response;
import okhttp3.WebSocket;
import okhttp3.WebSocketListener;

/**
 * Persistent WebSocket client that sends clipboard.update messages to the
 * Django backend using the Phase 5 protocol.
 *
 * Connection lifecycle:
 * - connect() opens a new WebSocket connection asynchronously.
 * - Callbacks (onOpen, onMessage, onFailure, onClosed) fire on OkHttp's
 *   thread pool; all public methods are thread-safe.
 * - On failure, scheduleReconnect() waits for a backoff period and calls
 *   connect() again. Backoff sequence: 2 → 5 → 15 → 30 seconds (capped).
 * - close() terminates the connection and suppresses further reconnects.
 */
public class ClipboardWebSocketClient {

    private static final String TAG = "ClipboardWSClient";
    private static final long[] BACKOFF_SECONDS = {2L, 5L, 15L, 30L};

    private final String wsBaseUrl;
    private final String deviceId;
    private final StatusListener listener;
    private final OkHttpClient httpClient;

    private final AtomicReference<WebSocket> activeSocket = new AtomicReference<>();
    private final AtomicBoolean connected = new AtomicBoolean(false);
    private final AtomicBoolean closed = new AtomicBoolean(false);

    // Accessed only from the reconnect thread and the WebSocket callbacks;
    // kept as volatile so the reconnect thread sees the latest value.
    private volatile int backoffIndex = 0;

    /**
     * Callbacks invoked by the WebSocket client.
     * All callbacks are invoked on OkHttp's internal thread pool.
     */
    public interface StatusListener {
        void onConnected();
        void onDisconnected();
        void onAckReceived(String deviceId, String status);
        void onError(String code, String detail);
    }

    public ClipboardWebSocketClient(String wsBaseUrl, String deviceId, StatusListener listener) {
        this.wsBaseUrl = wsBaseUrl;
        this.deviceId = deviceId;
        this.listener = listener;
        this.httpClient = new OkHttpClient.Builder()
                .connectTimeout(10, TimeUnit.SECONDS)
                .readTimeout(0, TimeUnit.SECONDS)   // Persistent: no read timeout.
                .writeTimeout(10, TimeUnit.SECONDS)
                .build();
    }

    /** Open a new WebSocket connection asynchronously. */
    public void connect() {
        if (closed.get()) return;
        String url = wsBaseUrl.endsWith("/")
                ? wsBaseUrl + "?device_id=" + deviceId
                : wsBaseUrl + "/?device_id=" + deviceId;
        Log.i(TAG, "Connecting to " + url);
        Request request = new Request.Builder().url(url).build();
        httpClient.newWebSocket(request, new InternalListener());
    }

    /**
     * Send a clipboard.update message.
     *
     * @param content Plain text clipboard value; must not be empty.
     * @return true if the message was enqueued for delivery, false otherwise.
     */
    public boolean send(String content) {
        WebSocket ws = activeSocket.get();
        if (ws == null || !connected.get()) {
            Log.w(TAG, "Cannot send — not connected.");
            return false;
        }
        try {
            JSONObject payload = new JSONObject();
            payload.put("type", "clipboard.update");
            payload.put("device_id", deviceId);
            payload.put("content", content);
            boolean enqueued = ws.send(payload.toString());
            if (enqueued) {
                Log.i(TAG, "Sent clipboard.update (" + content.length() + " chars).");
            } else {
                Log.w(TAG, "WebSocket send buffer full; message dropped.");
            }
            return enqueued;
        } catch (JSONException e) {
            Log.e(TAG, "Failed to build clipboard.update payload.", e);
            return false;
        }
    }

    /**
     * Gracefully close the connection and suppress further reconnection attempts.
     * Safe to call more than once.
     */
    public void close() {
        closed.set(true);
        connected.set(false);
        WebSocket ws = activeSocket.getAndSet(null);
        if (ws != null) {
            ws.close(1000, "Service stopped.");
        }
        // Shut down the dispatcher thread pool to release resources.
        httpClient.dispatcher().executorService().shutdown();
    }

    /** Returns true when a WebSocket connection is currently open. */
    public boolean isConnected() {
        return connected.get();
    }

    // ------------------------------------------------------------------
    // OkHttp WebSocket callbacks
    // ------------------------------------------------------------------

    private class InternalListener extends WebSocketListener {

        @Override
        public void onOpen(WebSocket ws, Response response) {
            activeSocket.set(ws);
            connected.set(true);
            backoffIndex = 0;
            Log.i(TAG, "WebSocket connected.");
            if (listener != null) listener.onConnected();
        }

        @Override
        public void onMessage(WebSocket ws, String text) {
            Log.d(TAG, "Received: " + text);
            try {
                JSONObject msg = new JSONObject(text);
                String type = msg.optString("type");
                if ("clipboard.ack".equals(type)) {
                    String dev = msg.optString("device_id");
                    String status = msg.optString("status");
                    Log.i(TAG, "clipboard.ack: device=" + dev + " status=" + status);
                    if (listener != null) listener.onAckReceived(dev, status);
                } else if ("error".equals(type)) {
                    String code = msg.optString("code");
                    String detail = msg.optString("detail");
                    Log.w(TAG, "Server error: " + code + " — " + detail);
                    if (listener != null) listener.onError(code, detail);
                } else {
                    Log.d(TAG, "Unhandled message type: " + type);
                }
            } catch (JSONException e) {
                Log.e(TAG, "Failed to parse server message: " + text, e);
            }
        }

        @Override
        public void onFailure(WebSocket ws, Throwable t, Response response) {
            activeSocket.set(null);
            connected.set(false);
            Log.w(TAG, "WebSocket failure: " + t.getMessage());
            if (listener != null) listener.onDisconnected();
            scheduleReconnect();
        }

        @Override
        public void onClosed(WebSocket ws, int code, String reason) {
            activeSocket.set(null);
            connected.set(false);
            Log.i(TAG, "WebSocket closed: " + code + " " + reason);
            if (listener != null) listener.onDisconnected();
        }
    }

    // ------------------------------------------------------------------
    // Reconnection with bounded backoff
    // ------------------------------------------------------------------

    private void scheduleReconnect() {
        if (closed.get()) return;
        long delay = BACKOFF_SECONDS[Math.min(backoffIndex, BACKOFF_SECONDS.length - 1)];
        if (backoffIndex < BACKOFF_SECONDS.length - 1) backoffIndex++;
        Log.i(TAG, "Reconnecting in " + delay + " s.");
        Thread t = new Thread(() -> {
            try {
                Thread.sleep(delay * 1000L);
                connect();
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                Log.d(TAG, "Reconnect thread interrupted.");
            }
        }, "ws-reconnect");
        t.setDaemon(true);
        t.start();
    }
}

package com.clipboard.sync.api;

import android.util.Log;

import org.json.JSONException;
import org.json.JSONObject;

import java.io.IOException;
import java.util.concurrent.TimeUnit;

import okhttp3.Call;
import okhttp3.Callback;
import okhttp3.MediaType;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;
import okhttp3.ResponseBody;

/**
 * Asynchronous REST API client for requesting clipboard updates and pairing devices with Django.
 */
public class ClipboardApiClient {

    private static final String TAG = "ClipboardApiClient";
    private final OkHttpClient httpClient;

    public interface ApiCallback {
        void onSuccess(String content);
        void onNotFound();
        void onError(String errorMessage);
    }

    public interface PairCallback {
        void onSuccess(String status, int userId);
        void onError(int statusCode, String errorMessage);
    }

    public ClipboardApiClient() {
        this(new OkHttpClient.Builder()
                .connectTimeout(10, TimeUnit.SECONDS)
                .readTimeout(10, TimeUnit.SECONDS)
                .build());
    }

    public ClipboardApiClient(OkHttpClient httpClient) {
        this.httpClient = httpClient;
    }

    /**
     * Perform an HTTP GET request to retrieve the latest clipboard content.
     *
     * @param url      Target REST endpoint URL.
     * @param callback Callback invoked when response is available.
     */
    public void getLatestClipboard(String url, ApiCallback callback) {
        Request request = new Request.Builder()
                .url(url)
                .get()
                .build();

        httpClient.newCall(request).enqueue(new Callback() {
            @Override
            public void onFailure(Call call, IOException e) {
                logWarning(TAG, "HTTP request failed: " + e.getMessage());
                if (callback != null) {
                    callback.onError(e.getMessage());
                }
            }

            @Override
            public void onResponse(Call call, Response response) throws IOException {
                try (ResponseBody responseBody = response.body()) {
                    int statusCode = response.code();
                    if (statusCode == 200) {
                        if (responseBody == null) {
                            if (callback != null) callback.onError("Empty response body");
                            return;
                        }
                        String jsonString = responseBody.string();
                        if (jsonString == null || jsonString.trim().isEmpty() || !jsonString.trim().startsWith("{")) {
                            if (callback != null) callback.onError("Invalid JSON format");
                            return;
                        }
                        String content = parseContentFromJson(jsonString);
                        if (content.isEmpty()) {
                            if (callback != null) callback.onError("Clipboard entry content is empty.");
                        } else {
                            if (callback != null) callback.onSuccess(content);
                        }
                    } else if (statusCode == 404) {
                        if (callback != null) callback.onNotFound();
                    } else {
                        if (callback != null) callback.onError("HTTP " + statusCode);
                    }
                } catch (Throwable t) {
                    logError(TAG, "Unexpected error in response handler", t);
                    if (callback != null) callback.onError("Invalid JSON format");
                }
            }
        });
    }

    /**
     * Perform an HTTP POST request to pair this Android device with a Desktop device account using a pairing code.
     *
     * @param url             Target pairing endpoint URL.
     * @param pairingCode     Temporary pairing code (e.g. AB7K-29XM).
     * @param androidDeviceId Persistent Android device ID.
     * @param callback        Callback invoked when response is available.
     */
    public void pairDevice(String url, String pairingCode, String androidDeviceId, PairCallback callback) {
        try {
            String jsonPayload = "{\"code\":\"" + pairingCode + "\",\"android_device_id\":\"" + androidDeviceId + "\"}";

            RequestBody body = RequestBody.create(
                    jsonPayload,
                    MediaType.get("application/json; charset=utf-8")
            );

            Request request = new Request.Builder()
                    .url(url)
                    .post(body)
                    .build();

            httpClient.newCall(request).enqueue(new Callback() {
                @Override
                public void onFailure(Call call, IOException e) {
                    logWarning(TAG, "Pairing HTTP request failed: " + e.getMessage());
                    if (callback != null) callback.onError(0, e.getMessage());
                }

                @Override
                public void onResponse(Call call, Response response) throws IOException {
                    try (ResponseBody responseBody = response.body()) {
                        int statusCode = response.code();
                        String responseStr = responseBody != null ? responseBody.string() : "";
                        if (statusCode == 200) {
                            String statusVal = "paired";
                            int userIdVal = 0;
                            if (!responseStr.isEmpty() && responseStr.startsWith("{")) {
                                statusVal = parseJsonField(responseStr, "status", "paired");
                                String userStr = parseJsonField(responseStr, "user_id", "0");
                                try {
                                    userIdVal = Integer.parseInt(userStr);
                                } catch (NumberFormatException ignored) {}
                            }
                            if (callback != null) callback.onSuccess(statusVal, userIdVal);
                        } else {
                            String errorDetail = "Pairing failed (HTTP " + statusCode + ")";
                            if (!responseStr.isEmpty() && responseStr.startsWith("{")) {
                                String parsedMsg = parseJsonField(responseStr, "detail", "");
                                if (!parsedMsg.isEmpty()) {
                                    errorDetail = parsedMsg;
                                }
                            }
                            if (callback != null) callback.onError(statusCode, errorDetail);
                        }
                    } catch (Throwable t) {
                        logError(TAG, "Unexpected error in pairing response handler", t);
                        if (callback != null) callback.onError(0, "Invalid JSON response");
                    }
                }
            });
        } catch (Throwable t) {
            logError(TAG, "Failed to build pairing request payload", t);
            if (callback != null) callback.onError(0, "Invalid pairing request");
        }
    }

    public static String parseContentFromJson(String jsonString) {
        return parseJsonField(jsonString, "content", "");
    }

    public static String parseJsonField(String jsonString, String fieldName, String defaultValue) {
        if (jsonString == null) return defaultValue;
        try {
            JSONObject json = new JSONObject(jsonString);
            return json.optString(fieldName, defaultValue);
        } catch (Throwable t) {
            int index = jsonString.indexOf("\"" + fieldName + "\"");
            if (index != -1) {
                int colon = jsonString.indexOf(":", index);
                if (colon != -1) {
                    int startQuote = jsonString.indexOf("\"", colon);
                    if (startQuote != -1) {
                        int endQuote = jsonString.indexOf("\"", startQuote + 1);
                        if (endQuote != -1) {
                            return jsonString.substring(startQuote + 1, endQuote);
                        }
                    } else {
                        // Integer / boolean without quotes
                        int comma = jsonString.indexOf(",", colon);
                        int brace = jsonString.indexOf("}", colon);
                        int end = (comma != -1 && comma < brace) ? comma : brace;
                        if (end != -1) {
                            return jsonString.substring(colon + 1, end).trim();
                        }
                    }
                }
            }
            return defaultValue;
        }
    }

    private static void logWarning(String tag, String message) {
        try {
            Log.w(tag, message);
        } catch (Throwable ignored) {
            System.out.println(tag + ": " + message);
        }
    }

    private static void logError(String tag, String message, Throwable throwable) {
        try {
            Log.e(tag, message, throwable);
        } catch (Throwable ignored) {
            System.err.println(tag + ": " + message);
        }
    }
}

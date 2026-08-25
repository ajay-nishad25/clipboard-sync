package com.clipboard.sync.api;

import android.util.Log;

import org.json.JSONException;
import org.json.JSONObject;

import java.io.IOException;
import java.util.concurrent.TimeUnit;

import okhttp3.Call;
import okhttp3.Callback;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.Response;
import okhttp3.ResponseBody;

/**
 * Asynchronous REST API client for requesting the latest clipboard entry from Django.
 */
public class ClipboardApiClient {

    private static final String TAG = "ClipboardApiClient";
    private final OkHttpClient httpClient;

    public interface ApiCallback {
        void onSuccess(String content);
        void onNotFound();
        void onError(String errorMessage);
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

    public static String parseContentFromJson(String jsonString) {
        if (jsonString == null) return "";
        try {
            JSONObject json = new JSONObject(jsonString);
            return json.optString("content", "");
        } catch (Throwable t) {
            int index = jsonString.indexOf("\"content\"");
            if (index != -1) {
                int colon = jsonString.indexOf(":", index);
                if (colon != -1) {
                    int startQuote = jsonString.indexOf("\"", colon);
                    if (startQuote != -1) {
                        int endQuote = jsonString.indexOf("\"", startQuote + 1);
                        if (endQuote != -1) {
                            return jsonString.substring(startQuote + 1, endQuote);
                        }
                    }
                }
            }
            return "";
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

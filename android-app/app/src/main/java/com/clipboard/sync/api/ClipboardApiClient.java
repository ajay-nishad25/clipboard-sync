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
        this.httpClient = new OkHttpClient.Builder()
                .connectTimeout(10, TimeUnit.SECONDS)
                .readTimeout(10, TimeUnit.SECONDS)
                .build();
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
                Log.w(TAG, "HTTP request failed: " + e.getMessage());
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
                        JSONObject json = new JSONObject(jsonString);
                        String content = json.optString("content", "");
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
                } catch (JSONException e) {
                    Log.e(TAG, "Failed to parse JSON response", e);
                    if (callback != null) callback.onError("Invalid JSON format");
                }
            }
        });
    }
}

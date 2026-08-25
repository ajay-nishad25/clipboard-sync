package com.clipboard.sync.api;

import org.junit.Test;

import java.io.IOException;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicReference;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;

import okhttp3.MediaType;
import okhttp3.OkHttpClient;
import okhttp3.Protocol;
import okhttp3.Response;
import okhttp3.ResponseBody;

/**
 * Unit tests for ClipboardApiClient response parsing and error handling.
 */
public class ClipboardApiClientTest {

    private OkHttpClient createMockHttpClient(final int code, final String responseBodyString, final IOException exceptionToThrow) {
        return new OkHttpClient.Builder()
                .addInterceptor(chain -> {
                    if (exceptionToThrow != null) {
                        throw exceptionToThrow;
                    }
                    ResponseBody body = ResponseBody.create(
                            responseBodyString != null ? responseBodyString : "",
                            MediaType.get("application/json")
                    );
                    return new Response.Builder()
                            .request(chain.request())
                            .protocol(Protocol.HTTP_1_1)
                            .code(code)
                            .message(code == 200 ? "OK" : (code == 404 ? "Not Found" : "Error"))
                            .body(body)
                            .build();
                })
                .build();
    }

    @Test
    public void testSuccessful200ResponseExtractedContent() throws Exception {
        OkHttpClient client = createMockHttpClient(200, "{\"content\":\"Hello from Android Test\"}", null);
        ClipboardApiClient apiClient = new ClipboardApiClient(client);

        final CountDownLatch latch = new CountDownLatch(1);
        final AtomicReference<String> resultRef = new AtomicReference<>();

        apiClient.getLatestClipboard("http://localhost/api/clipboard/latest/", new ClipboardApiClient.ApiCallback() {
            @Override
            public void onSuccess(String content) {
                resultRef.set(content);
                latch.countDown();
            }

            @Override
            public void onNotFound() {}

            @Override
            public void onError(String errorMessage) {}
        });

        assertTrue(latch.await(5, TimeUnit.SECONDS));
        assertEquals("Hello from Android Test", resultRef.get());
    }

    @Test
    public void test404NotFoundResponse() throws Exception {
        OkHttpClient client = createMockHttpClient(404, "{\"detail\":\"Not found.\"}", null);
        ClipboardApiClient apiClient = new ClipboardApiClient(client);

        final CountDownLatch latch = new CountDownLatch(1);
        final AtomicBoolean notFoundCalled = new AtomicBoolean(false);

        apiClient.getLatestClipboard("http://localhost/api/clipboard/latest/", new ClipboardApiClient.ApiCallback() {
            @Override
            public void onSuccess(String content) {}

            @Override
            public void onNotFound() {
                notFoundCalled.set(true);
                latch.countDown();
            }

            @Override
            public void onError(String errorMessage) {}
        });

        assertTrue(latch.await(5, TimeUnit.SECONDS));
        assertTrue(notFoundCalled.get());
    }

    @Test
    public void testNetworkFailureHandled() throws Exception {
        OkHttpClient client = createMockHttpClient(500, null, new IOException("Connection refused"));
        ClipboardApiClient apiClient = new ClipboardApiClient(client);

        final CountDownLatch latch = new CountDownLatch(1);
        final AtomicReference<String> errorRef = new AtomicReference<>();

        apiClient.getLatestClipboard("http://localhost/api/clipboard/latest/", new ClipboardApiClient.ApiCallback() {
            @Override
            public void onSuccess(String content) {}

            @Override
            public void onNotFound() {}

            @Override
            public void onError(String errorMessage) {
                errorRef.set(errorMessage);
                latch.countDown();
            }
        });

        assertTrue(latch.await(5, TimeUnit.SECONDS));
        assertNotNull(errorRef.get());
        assertTrue(errorRef.get().contains("Connection refused"));
    }

    @Test
    public void testMalformedJsonHandled() throws Exception {
        OkHttpClient client = createMockHttpClient(200, "not-json", null);
        ClipboardApiClient apiClient = new ClipboardApiClient(client);

        final CountDownLatch latch = new CountDownLatch(1);
        final AtomicReference<String> errorRef = new AtomicReference<>();

        apiClient.getLatestClipboard("http://localhost/api/clipboard/latest/", new ClipboardApiClient.ApiCallback() {
            @Override
            public void onSuccess(String content) {}

            @Override
            public void onNotFound() {}

            @Override
            public void onError(String errorMessage) {
                errorRef.set(errorMessage);
                latch.countDown();
            }
        });

        assertTrue(latch.await(5, TimeUnit.SECONDS));
        assertEquals("Invalid JSON format", errorRef.get());
    }

    @Test
    public void testEmptyContentHandled() throws Exception {
        OkHttpClient client = createMockHttpClient(200, "{\"content\":\"\"}", null);
        ClipboardApiClient apiClient = new ClipboardApiClient(client);

        final CountDownLatch latch = new CountDownLatch(1);
        final AtomicReference<String> errorRef = new AtomicReference<>();

        apiClient.getLatestClipboard("http://localhost/api/clipboard/latest/", new ClipboardApiClient.ApiCallback() {
            @Override
            public void onSuccess(String content) {}

            @Override
            public void onNotFound() {}

            @Override
            public void onError(String errorMessage) {
                errorRef.set(errorMessage);
                latch.countDown();
            }
        });

        assertTrue(latch.await(5, TimeUnit.SECONDS));
        assertEquals("Clipboard entry content is empty.", errorRef.get());
    }
}

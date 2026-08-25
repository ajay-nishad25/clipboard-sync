package com.clipboard.sync.api;

import org.junit.Test;

import java.io.IOException;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;
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
 * Unit tests for ClipboardApiClient response parsing, token authentication, and pairing.
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
                            .message(code == 200 ? "OK" : (code == 404 ? "Not Found" : (code == 409 ? "Conflict" : "Error")))
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

        apiClient.getLatestClipboard("http://localhost/api/clipboard/latest/", "devtok_test", new ClipboardApiClient.ApiCallback() {
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

        apiClient.getLatestClipboard("http://localhost/api/clipboard/latest/", "devtok_test", new ClipboardApiClient.ApiCallback() {
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

        apiClient.getLatestClipboard("http://localhost/api/clipboard/latest/", "devtok_test", new ClipboardApiClient.ApiCallback() {
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

        apiClient.getLatestClipboard("http://localhost/api/clipboard/latest/", "devtok_test", new ClipboardApiClient.ApiCallback() {
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

        apiClient.getLatestClipboard("http://localhost/api/clipboard/latest/", "devtok_test", new ClipboardApiClient.ApiCallback() {
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

    @Test
    public void testPairDeviceSuccess() throws Exception {
        OkHttpClient client = createMockHttpClient(200, "{\"status\":\"paired\",\"device_id\":\"android-100\",\"credential\":\"devtok_sec123\",\"user_id\":42}", null);
        ClipboardApiClient apiClient = new ClipboardApiClient(client);

        final CountDownLatch latch = new CountDownLatch(1);
        final AtomicReference<String> statusRef = new AtomicReference<>();
        final AtomicReference<String> tokenRef = new AtomicReference<>();
        final AtomicInteger userIdRef = new AtomicInteger();

        apiClient.pairDevice("http://localhost/api/device/pair/", "AB7K-29XM", "android-100", new ClipboardApiClient.PairCallback() {
            @Override
            public void onSuccess(String status, String credential, int userId) {
                statusRef.set(status);
                tokenRef.set(credential);
                userIdRef.set(userId);
                latch.countDown();
            }

            @Override
            public void onError(int statusCode, String errorMessage) {}
        });

        assertTrue(latch.await(5, TimeUnit.SECONDS));
        assertEquals("paired", statusRef.get());
        assertEquals("devtok_sec123", tokenRef.get());
        assertEquals(42, userIdRef.get());
    }

    @Test
    public void testPairDeviceInvalidCodeError() throws Exception {
        OkHttpClient client = createMockHttpClient(400, "{\"detail\":\"Invalid or unknown pairing code.\"}", null);
        ClipboardApiClient apiClient = new ClipboardApiClient(client);

        final CountDownLatch latch = new CountDownLatch(1);
        final AtomicInteger codeRef = new AtomicInteger();
        final AtomicReference<String> msgRef = new AtomicReference<>();

        apiClient.pairDevice("http://localhost/api/device/pair/", "INVALID", "android-100", new ClipboardApiClient.PairCallback() {
            @Override
            public void onSuccess(String status, String credential, int userId) {}

            @Override
            public void onError(int statusCode, String errorMessage) {
                codeRef.set(statusCode);
                msgRef.set(errorMessage);
                latch.countDown();
            }
        });

        assertTrue(latch.await(5, TimeUnit.SECONDS));
        assertEquals(400, codeRef.get());
        assertEquals("Invalid or unknown pairing code.", msgRef.get());
    }

    @Test
    public void testPairDeviceConflictError() throws Exception {
        OkHttpClient client = createMockHttpClient(409, "{\"detail\":\"Device is already paired with another user account.\"}", null);
        ClipboardApiClient apiClient = new ClipboardApiClient(client);

        final CountDownLatch latch = new CountDownLatch(1);
        final AtomicInteger codeRef = new AtomicInteger();
        final AtomicReference<String> msgRef = new AtomicReference<>();

        apiClient.pairDevice("http://localhost/api/device/pair/", "AB7K-29XM", "android-100", new ClipboardApiClient.PairCallback() {
            @Override
            public void onSuccess(String status, String credential, int userId) {}

            @Override
            public void onError(int statusCode, String errorMessage) {
                codeRef.set(statusCode);
                msgRef.set(errorMessage);
                latch.countDown();
            }
        });

        assertTrue(latch.await(5, TimeUnit.SECONDS));
        assertEquals(409, codeRef.get());
        assertEquals("Device is already paired with another user account.", msgRef.get());
    }
}

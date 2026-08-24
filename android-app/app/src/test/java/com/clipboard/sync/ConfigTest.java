package com.clipboard.sync;

import org.junit.Test;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;

/**
 * Unit tests for Android app constants and configuration defaults.
 */
public class ConfigTest {

    @Test
    public void testWebSocketBaseUrlDefault() {
        assertNotNull(Config.WS_BASE_URL);
        assertTrue(Config.WS_BASE_URL.startsWith("ws://"));
        assertTrue(Config.WS_BASE_URL.endsWith("/ws/clipboard/"));
    }

    @Test
    public void testRestLatestUrlDefault() {
        assertNotNull(Config.REST_LATEST_URL);
        assertTrue(Config.REST_LATEST_URL.startsWith("http://"));
        assertTrue(Config.REST_LATEST_URL.endsWith("/api/clipboard/latest/"));
    }

    @Test
    public void testDeviceIdDefault() {
        assertEquals("android-001", Config.DEVICE_ID);
    }

    @Test
    public void testNotificationChannelConstants() {
        assertEquals("clipboard_sync_channel", Config.NOTIFICATION_CHANNEL_ID);
        assertEquals(1, Config.NOTIFICATION_ID);
    }
}

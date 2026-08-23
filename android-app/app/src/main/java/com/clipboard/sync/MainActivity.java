package com.clipboard.sync;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.widget.Button;
import android.widget.TextView;

import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;

/**
 * Main entry point. Provides a Start/Stop button for the clipboard monitor
 * foreground service and displays the current connection status and recent
 * sync events received via local broadcast from ClipboardMonitorService.
 */
public class MainActivity extends AppCompatActivity {

    private static final String TAG = "MainActivity";
    private static final int REQ_NOTIFICATION_PERMISSION = 1001;

    private TextView statusText;
    private TextView logText;
    private Button toggleButton;
    private boolean serviceRunning = false;

    /**
     * Receives status broadcasts from ClipboardMonitorService and updates the UI.
     * Registered with RECEIVER_NOT_EXPORTED so only our own service can deliver.
     */
    private final BroadcastReceiver statusReceiver = new BroadcastReceiver() {
        @Override
        public void onReceive(Context context, Intent intent) {
            String message = intent.getStringExtra(ClipboardMonitorService.EXTRA_STATUS_MESSAGE);
            String lastContent = intent.getStringExtra(ClipboardMonitorService.EXTRA_LAST_CONTENT);
            if (message != null) {
                statusText.setText(message);
            }
            if (lastContent != null) {
                appendLog("Synced: " + truncate(lastContent, 80));
            }
        }
    };

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        statusText   = findViewById(R.id.statusText);
        logText      = findViewById(R.id.logText);
        toggleButton = findViewById(R.id.toggleButton);

        toggleButton.setOnClickListener(v -> toggleService());
        requestNotificationPermissionIfNeeded();
    }

    @Override
    protected void onResume() {
        super.onResume();
        IntentFilter filter = new IntentFilter(ClipboardMonitorService.ACTION_STATUS_UPDATE);
        // RECEIVER_NOT_EXPORTED: only broadcasts from this app (same UID) are delivered.
        ContextCompat.registerReceiver(this, statusReceiver, filter,
                ContextCompat.RECEIVER_NOT_EXPORTED);
    }

    @Override
    protected void onPause() {
        super.onPause();
        unregisterReceiver(statusReceiver);
    }

    private void toggleService() {
        if (serviceRunning) {
            stopService(new Intent(this, ClipboardMonitorService.class));
            serviceRunning = false;
            statusText.setText(R.string.status_stopped);
            toggleButton.setText(R.string.btn_start);
            appendLog("Service stopped.");
        } else {
            ContextCompat.startForegroundService(
                    this, new Intent(this, ClipboardMonitorService.class));
            serviceRunning = true;
            statusText.setText(R.string.status_starting);
            toggleButton.setText(R.string.btn_stop);
            appendLog("Service starting\u2026");
        }
    }

    /** Prepend the newest log line at the top so the most recent event is visible. */
    private void appendLog(String line) {
        String current = logText.getText().toString();
        logText.setText(current.isEmpty() ? line : line + "\n" + current);
    }

    private static String truncate(String s, int max) {
        return s.length() > max ? s.substring(0, max) + "\u2026" : s;
    }

    private void requestNotificationPermissionIfNeeded() {
        if (Build.VERSION.SDK_INT >= 33) {
            if (ContextCompat.checkSelfPermission(this,
                    android.Manifest.permission.POST_NOTIFICATIONS)
                    != PackageManager.PERMISSION_GRANTED) {
                ActivityCompat.requestPermissions(this,
                        new String[]{android.Manifest.permission.POST_NOTIFICATIONS},
                        REQ_NOTIFICATION_PERMISSION);
            }
        }
    }
}

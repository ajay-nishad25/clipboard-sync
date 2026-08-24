package com.clipboard.sync;

import android.content.BroadcastReceiver;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.util.Log;
import android.widget.Button;
import android.widget.TextView;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;

import com.clipboard.sync.api.ClipboardApiClient;

/**
 * Main entry point for Clipboard Sync.
 * Provides user-controlled [SEND CLIPBOARD] and [RECEIVE CLIPBOARD] actions,
 * along with a Start/Stop service toggle and real-time status updates.
 */
public class MainActivity extends AppCompatActivity {

    private static final String TAG = "MainActivity";
    private static final int REQ_NOTIFICATION_PERMISSION = 1001;

    private TextView statusText;
    private TextView logText;
    private Button sendButton;
    private Button receiveButton;
    private Button toggleButton;

    private boolean serviceRunning = false;
    private boolean isSending = false;
    private ClipboardApiClient apiClient;

    /**
     * Receives status broadcasts from ClipboardMonitorService and updates the UI.
     */
    private final BroadcastReceiver statusReceiver = new BroadcastReceiver() {
        @Override
        public void onReceive(Context context, Intent intent) {
            String message = intent.getStringExtra(ClipboardMonitorService.EXTRA_STATUS_MESSAGE);
            String lastContent = intent.getStringExtra(ClipboardMonitorService.EXTRA_LAST_CONTENT);
            boolean isAck = intent.getBooleanExtra(ClipboardMonitorService.EXTRA_IS_ACK, false);
            boolean isSuccess = intent.getBooleanExtra(ClipboardMonitorService.EXTRA_IS_SUCCESS, false);

            if (isAck) {
                isSending = false;
                if (isSuccess) {
                    statusText.setText(R.string.status_sent_success);
                    if (lastContent != null) {
                        appendLog("Sent: " + lastContent.length() + " chars");
                    }
                } else {
                    statusText.setText(message != null ? message : getString(R.string.status_send_failed));
                }
            } else if (!isSending && message != null) {
                statusText.setText(message);
            }
        }
    };

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        apiClient     = new ClipboardApiClient();
        statusText    = findViewById(R.id.statusText);
        logText       = findViewById(R.id.logText);
        sendButton    = findViewById(R.id.sendButton);
        receiveButton = findViewById(R.id.receiveButton);
        toggleButton  = findViewById(R.id.toggleButton);

        sendButton.setOnClickListener(v -> sendClipboard());
        receiveButton.setOnClickListener(v -> receiveClipboard());
        toggleButton.setOnClickListener(v -> toggleService());

        requestNotificationPermissionIfNeeded();
    }

    @Override
    protected void onResume() {
        super.onResume();
        IntentFilter filter = new IntentFilter(ClipboardMonitorService.ACTION_STATUS_UPDATE);
        ContextCompat.registerReceiver(this, statusReceiver, filter,
                ContextCompat.RECEIVER_NOT_EXPORTED);
    }

    @Override
    protected void onPause() {
        super.onPause();
        unregisterReceiver(statusReceiver);
    }

    // ------------------------------------------------------------------
    // SEND CLIPBOARD WORKFLOW
    // ------------------------------------------------------------------

    private void sendClipboard() {
        if (!serviceRunning) {
            statusText.setText(R.string.status_please_start);
            Toast.makeText(this, R.string.status_please_start, Toast.LENGTH_SHORT).show();
            return;
        }

        ClipboardManager cm = (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
        if (cm == null) {
            statusText.setText(R.string.status_clipboard_empty);
            return;
        }

        try {
            ClipData clip = cm.getPrimaryClip();
            if (clip == null || clip.getItemCount() == 0) {
                statusText.setText(R.string.status_clipboard_empty);
                Toast.makeText(this, R.string.status_clipboard_empty, Toast.LENGTH_SHORT).show();
                return;
            }

            CharSequence raw = clip.getItemAt(0).getText();
            if (raw == null || raw.length() == 0) {
                statusText.setText(R.string.status_clipboard_empty);
                Toast.makeText(this, R.string.status_clipboard_empty, Toast.LENGTH_SHORT).show();
                return;
            }

            String content = raw.toString();
            isSending = true;
            statusText.setText(R.string.status_sending);

            Intent serviceIntent = new Intent(this, ClipboardMonitorService.class);
            serviceIntent.setAction(ClipboardMonitorService.ACTION_SEND_CLIPBOARD);
            serviceIntent.putExtra(ClipboardMonitorService.EXTRA_CLIPBOARD_TEXT, content);
            ContextCompat.startForegroundService(this, serviceIntent);

        } catch (SecurityException e) {
            Log.w(TAG, "Clipboard access denied: " + e.getMessage());
            statusText.setText(R.string.status_clipboard_empty);
        }
    }

    // ------------------------------------------------------------------
    // RECEIVE CLIPBOARD WORKFLOW
    // ------------------------------------------------------------------

    private void receiveClipboard() {
        statusText.setText(R.string.status_receiving);

        apiClient.getLatestClipboard(Config.REST_LATEST_URL, new ClipboardApiClient.ApiCallback() {
            @Override
            public void onSuccess(String content) {
                runOnUiThread(() -> {
                    ClipboardManager cm = (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
                    if (cm != null) {
                        cm.setPrimaryClip(ClipData.newPlainText("clipboard_sync", content));
                        statusText.setText(R.string.status_received_success);
                        appendLog("Received: " + content.length() + " chars");
                        Toast.makeText(MainActivity.this, R.string.status_received_success, Toast.LENGTH_SHORT).show();
                    } else {
                        statusText.setText(getString(R.string.status_receive_failed, "ClipboardManager unavailable"));
                    }
                });
            }

            @Override
            public void onNotFound() {
                runOnUiThread(() -> {
                    statusText.setText(R.string.status_no_entries);
                    Toast.makeText(MainActivity.this, R.string.status_no_entries, Toast.LENGTH_SHORT).show();
                });
            }

            @Override
            public void onError(String errorMessage) {
                runOnUiThread(() -> {
                    String failureText = getString(R.string.status_receive_failed, errorMessage);
                    statusText.setText(failureText);
                    Toast.makeText(MainActivity.this, failureText, Toast.LENGTH_SHORT).show();
                });
            }
        });
    }

    // ------------------------------------------------------------------
    // SERVICE CONTROL
    // ------------------------------------------------------------------

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

    private void appendLog(String line) {
        String current = logText.getText().toString();
        logText.setText(current.isEmpty() ? line : line + "\n" + current);
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

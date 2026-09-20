package org.garden.relay;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.ActivityNotFoundException;
import android.content.ClipData;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.content.pm.ResolveInfo;
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.provider.Settings;
import android.view.View;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import androidx.core.content.FileProvider;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public final class MainActivity extends Activity {
    private static final String PREF_JOB_URL = "job_url";
    private static final String PREF_AUTO_SEND = "auto_send";
    private static final String PREF_AUTO_ADVANCE = "auto_advance";
    private static final String PREF_AUTO_RETURN = "auto_return";
    private static final String PREF_ACTIVE_JOB = "active_job";
    private static final String PREF_ACTIVE_SLOT = "active_slot";
    private static final String PREF_PENDING_SEND_PACKAGE = "pending_send_package";
    private static final String PREF_PENDING_SEND_UNTIL = "pending_send_until";

    private final ExecutorService io = Executors.newSingleThreadExecutor();
    private final Handler main = new Handler(Looper.getMainLooper());
    private final Map<String, Button> bindButtons = new LinkedHashMap<>();

    private TextView statusView;
    private ReviewJob currentJob;
    private CheckBox autoSend;
    private CheckBox autoAdvance;
    private CheckBox autoReturn;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        buildUi();
        handleIncoming(getIntent());
        refreshJob(false);
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        handleIncoming(intent);
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        io.shutdownNow();
    }

    private SharedPreferences prefs() {
        return AppBindings.prefs(this);
    }

    private void buildUi() {
        ScrollView scroll = new ScrollView(this);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        int pad = dp(18);
        root.setPadding(pad, pad, pad, pad);
        scroll.addView(root);

        TextView title = new TextView(this);
        title.setText("Garden Relay");
        title.setTextSize(28);
        root.addView(title);

        TextView subtitle = new TextView(this);
        subtitle.setText("Phone review bus — bind each model app once, then relay frozen jobs and exact results without copy/paste.");
        subtitle.setTextSize(15);
        subtitle.setPadding(0, dp(8), 0, dp(14));
        root.addView(subtitle);

        statusView = new TextView(this);
        statusView.setText("Loading job…");
        statusView.setTextSize(14);
        statusView.setPadding(0, 0, 0, dp(14));
        root.addView(statusView);

        addBinding(root, "deepseek", "DeepSeek");
        addBinding(root, "qwen", "Qwen");
        addBinding(root, "gemini", "Gemini");
        addBinding(root, "chatgpt", "ChatGPT");

        Button refresh = button("Refresh review job", v -> refreshJob(false));
        root.addView(refresh);

        Button run = button("Run next reviewer", v -> runNextReviewer());
        root.addView(run);

        Button share = button("Share completed bundle to ChatGPT", v -> shareBundleToChatGpt());
        root.addView(share);

        Button jobUrl = button("Review job source", v -> editJobUrl());
        root.addView(jobUrl);

        autoAdvance = new CheckBox(this);
        autoAdvance.setText("Automatically open the next reviewer after a result is shared back");
        autoAdvance.setChecked(prefs().getBoolean(PREF_AUTO_ADVANCE, true));
        autoAdvance.setOnCheckedChangeListener((b, checked) -> prefs().edit().putBoolean(PREF_AUTO_ADVANCE, checked).apply());
        root.addView(autoAdvance);

        autoReturn = new CheckBox(this);
        autoReturn.setText("Automatically return the completed result bundle to ChatGPT");
        autoReturn.setChecked(prefs().getBoolean(PREF_AUTO_RETURN, true));
        autoReturn.setOnCheckedChangeListener((b, checked) -> prefs().edit().putBoolean(PREF_AUTO_RETURN, checked).apply());
        root.addView(autoReturn);

        autoSend = new CheckBox(this);
        autoSend.setText("One-shot Accessibility helper: tap Send automatically when exactly one safe Send/Submit button is found");
        autoSend.setChecked(prefs().getBoolean(PREF_AUTO_SEND, false));
        autoSend.setOnCheckedChangeListener((b, checked) -> prefs().edit().putBoolean(PREF_AUTO_SEND, checked).apply());
        root.addView(autoSend);

        Button accessibility = button("Open Accessibility settings", v ->
                startActivity(new Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)));
        root.addView(accessibility);

        TextView privacy = new TextView(this);
        privacy.setText("\nPrivacy: no clipboard monitoring, no screen recording, no password/API-key storage, and no continuous accessibility capture. The helper is armed only for a bound app for a short one-shot Send action.");
        privacy.setTextSize(12);
        root.addView(privacy);

        setContentView(scroll);
        refreshBindingLabels();
    }

    private void addBinding(LinearLayout root, String slot, String label) {
        Button button = button("Bind " + label, v -> bindSlot(slot, label));
        bindButtons.put(slot, button);
        root.addView(button);
    }

    private Button button(String text, View.OnClickListener listener) {
        Button b = new Button(this);
        b.setAllCaps(false);
        b.setText(text);
        b.setOnClickListener(listener);
        return b;
    }

    private void refreshBindingLabels() {
        for (String slot : AppBindings.SLOTS) {
            Button button = bindButtons.get(slot);
            if (button == null) continue;
            String boundLabel = AppBindings.labelFor(this, slot);
            if (boundLabel.trim().isEmpty()) {
                button.setText("Bind " + prettySlot(slot));
            } else {
                button.setText(prettySlot(slot) + " → " + boundLabel);
            }
        }
    }

    private void bindSlot(String slot, String label) {
        List<ResolveInfo> apps = shareCapableApps();
        if (apps.isEmpty()) {
            toast("No share-capable apps found.");
            return;
        }

        CharSequence[] labels = new CharSequence[apps.size()];
        for (int i = 0; i < apps.size(); i++) {
            ResolveInfo ri = apps.get(i);
            labels[i] = ri.loadLabel(getPackageManager()) + "  (" + ri.activityInfo.packageName + ")";
        }

        new AlertDialog.Builder(this)
                .setTitle("Choose installed app for " + label)
                .setItems(labels, (dialog, which) -> {
                    ResolveInfo ri = apps.get(which);
                    String appLabel = String.valueOf(ri.loadLabel(getPackageManager()));
                    AppBindings.bind(this, slot, ri.activityInfo.packageName, appLabel);
                    refreshBindingLabels();
                    toast(label + " bound to " + appLabel);
                })
                .setNegativeButton("Cancel", null)
                .show();
    }

    private List<ResolveInfo> shareCapableApps() {
        Intent intent = new Intent(Intent.ACTION_SEND);
        intent.setType("text/plain");
        intent.putExtra(Intent.EXTRA_TEXT, "Garden Relay capability probe");

        List<ResolveInfo> raw = getPackageManager().queryIntentActivities(intent, PackageManager.MATCH_DEFAULT_ONLY);
        Map<String, ResolveInfo> unique = new LinkedHashMap<>();
        for (ResolveInfo ri : raw) {
            if (ri.activityInfo == null) continue;
            String pkg = ri.activityInfo.packageName;
            if (getPackageName().equals(pkg)) continue;
            unique.putIfAbsent(pkg, ri);
        }
        List<ResolveInfo> out = new ArrayList<>(unique.values());
        out.sort(Comparator.comparing(a -> String.valueOf(a.loadLabel(getPackageManager())).toLowerCase()));
        return out;
    }

    private void refreshJob(boolean runAfter) {
        String url = prefs().getString(PREF_JOB_URL, JobClient.DEFAULT_JOB_URL);
        status("Fetching job…\n" + url);
        io.execute(() -> {
            try {
                ReviewJob job = JobClient.fetchJob(url);
                main.post(() -> {
                    currentJob = job;
                    renderJobStatus();
                    if (runAfter && "READY".equalsIgnoreCase(job.status)) runNextReviewer();
                });
            } catch (Exception e) {
                main.post(() -> status("Job fetch unavailable: " + e.getMessage() +
                        "\nYou can still bind/test apps. No review is launched until a READY job exists."));
            }
        });
    }

    private void renderJobStatus() {
        if (currentJob == null) {
            status("No job loaded.");
            return;
        }
        StringBuilder sb = new StringBuilder();
        sb.append(currentJob.title).append("\n")
                .append("job_id: ").append(currentJob.jobId).append("\n")
                .append("status: ").append(currentJob.status).append("\n");
        for (ReviewJob.Target t : currentJob.targets) {
            boolean done = ResultStore.hasResult(this, currentJob.jobId, t.slot);
            sb.append(done ? "✓ " : "○ ").append(t.displayName)
                    .append(" — ").append(t.attachments.size()).append(" attachment(s)\n");
        }
        status(sb.toString());
    }

    private void runNextReviewer() {
        if (currentJob == null) {
            refreshJob(true);
            return;
        }
        if (!"READY".equalsIgnoreCase(currentJob.status)) {
            toast("Current job is " + currentJob.status + ", not READY.");
            return;
        }

        for (ReviewJob.Target target : currentJob.targets) {
            if ("chatgpt".equals(target.slot)) continue; // ChatGPT is the result destination, not an external phone reviewer.
            if (!ResultStore.hasResult(this, currentJob.jobId, target.slot)) {
                sendTarget(target);
                return;
            }
        }
        toast("All external reviewer results are present.");
        renderJobStatus();
        if (prefs().getBoolean(PREF_AUTO_RETURN, true)) {
            main.postDelayed(this::shareBundleToChatGpt, 500);
        }
    }

    private void sendTarget(ReviewJob.Target target) {
        String pkg = AppBindings.packageFor(this, target.slot);
        if (pkg.trim().isEmpty()) {
            bindSlot(target.slot, target.displayName);
            toast("Bind " + target.displayName + " once, then tap Run next reviewer again.");
            return;
        }

        status("Preparing " + target.displayName + "…");
        io.execute(() -> {
            try {
                List<File> attachments = JobClient.downloadAttachments(this, currentJob, target);
                main.post(() -> launchShare(target, pkg, attachments));
            } catch (Exception e) {
                main.post(() -> {
                    status("Could not prepare " + target.displayName + ": " + e.getMessage());
                    toast("Review packet failed integrity/download check.");
                });
            }
        });
    }

    private void launchShare(ReviewJob.Target target, String pkg, List<File> attachments) {
        try {
            Intent intent = buildShareIntent(target, pkg, attachments);
            if (intent.resolveActivity(getPackageManager()) == null && attachments.size() > 1) {
                File combined = buildCombinedInput(currentJob, target, attachments);
                ArrayList<File> singleCombined = new ArrayList<>();
                singleCombined.add(combined);
                intent = buildShareIntent(target, pkg, singleCombined);
            }

            if (intent.resolveActivity(getPackageManager()) == null) {
                toast(target.displayName + " does not expose a compatible Android share target.");
                return;
            }

            prefs().edit()
                    .putString(PREF_ACTIVE_JOB, currentJob.jobId)
                    .putString(PREF_ACTIVE_SLOT, target.slot)
                    .apply();

            if (prefs().getBoolean(PREF_AUTO_SEND, false)) {
                prefs().edit()
                        .putString(PREF_PENDING_SEND_PACKAGE, pkg)
                        .putLong(PREF_PENDING_SEND_UNTIL, System.currentTimeMillis() + 120_000L)
                        .apply();
            }

            startActivity(intent);
        } catch (Exception e) {
            toast("Cannot open " + target.displayName + ": " + e.getMessage());
        }
    }

    private Intent buildShareIntent(ReviewJob.Target target, String pkg, List<File> attachments) {
        final Intent intent;
        if (attachments.size() <= 1) {
            intent = new Intent(Intent.ACTION_SEND);
            intent.setType(attachments.isEmpty() ? "text/plain" : "text/plain");
            if (!attachments.isEmpty()) {
                Uri uri = fileUri(attachments.get(0));
                intent.putExtra(Intent.EXTRA_STREAM, uri);
                intent.setClipData(ClipData.newRawUri(attachments.get(0).getName(), uri));
            }
        } else {
            intent = new Intent(Intent.ACTION_SEND_MULTIPLE);
            intent.setType("*/*");
            ArrayList<Uri> uris = new ArrayList<>();
            ClipData clip = null;
            for (File file : attachments) {
                Uri uri = fileUri(file);
                uris.add(uri);
                if (clip == null) clip = ClipData.newRawUri(file.getName(), uri);
                else clip.addItem(new ClipData.Item(uri));
            }
            intent.putParcelableArrayListExtra(Intent.EXTRA_STREAM, uris);
            intent.setClipData(clip);
        }
        intent.putExtra(Intent.EXTRA_TEXT, target.prompt);
        intent.putExtra(Intent.EXTRA_SUBJECT, "Garden review " + currentJob.jobId + " — " + target.displayName);
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
        intent.setPackage(pkg);
        for (File file : attachments) {
            grantUriPermission(pkg, fileUri(file), Intent.FLAG_GRANT_READ_URI_PERMISSION);
        }
        return intent;
    }

    private File buildCombinedInput(ReviewJob job, ReviewJob.Target target, List<File> attachments) throws Exception {
        File dir = new File(getCacheDir(), "jobs/" + safe(job.jobId) + "/" + safe(target.slot));
        if (!dir.exists()) dir.mkdirs();
        File out = new File(dir, "GARDEN_REVIEW_" + safe(job.jobId) + "_" + safe(target.slot) + ".txt");
        StringBuilder sb = new StringBuilder();
        sb.append(target.prompt).append("\n\n");
        for (File file : attachments) {
            byte[] raw = readAll(file);
            sb.append("\n===== ATTACHMENT ").append(file.getName()).append(" =====\n");
            sb.append("SHA256: ").append(Hashing.sha256(raw)).append("\n");
            sb.append(new String(raw, StandardCharsets.UTF_8));
            if (raw.length == 0 || raw[raw.length - 1] != '\n') sb.append("\n");
            sb.append("===== END ATTACHMENT =====\n");
        }
        try (java.io.FileOutputStream stream = new java.io.FileOutputStream(out)) {
            stream.write(sb.toString().getBytes(StandardCharsets.UTF_8));
        }
        return out;
    }

    private Uri fileUri(File file) {
        return FileProvider.getUriForFile(this, getPackageName() + ".files", file);
    }

    private void handleIncoming(Intent intent) {
        if (intent == null) return;
        String action = intent.getAction();
        if (!Intent.ACTION_SEND.equals(action) && !Intent.ACTION_SEND_MULTIPLE.equals(action)) return;

        String jobId = prefs().getString(PREF_ACTIVE_JOB, "");
        String slot = prefs().getString(PREF_ACTIVE_SLOT, "");
        if (jobId.trim().isEmpty() || slot.trim().isEmpty()) {
            toast("Received a share, but no reviewer is currently armed. Result was not assigned.");
            return;
        }

        io.execute(() -> {
            try {
                Incoming incoming = readIncoming(intent);
                ResultStore.save(this, jobId, slot, incoming.bytes, incoming.kind);
                prefs().edit()
                        .remove(PREF_ACTIVE_SLOT)
                        .remove(PREF_PENDING_SEND_PACKAGE)
                        .remove(PREF_PENDING_SEND_UNTIL)
                        .apply();
                main.post(() -> {
                    toast("Saved exact " + prettySlot(slot) + " result.");
                    if (currentJob != null && currentJob.jobId.equals(jobId)) renderJobStatus();
                    if (prefs().getBoolean(PREF_AUTO_ADVANCE, true)) {
                        main.postDelayed(() -> refreshJob(true), 700);
                    }
                });
            } catch (Exception e) {
                main.post(() -> toast("Could not store shared result: " + e.getMessage()));
            }
        });
    }

    private Incoming readIncoming(Intent intent) throws Exception {
        ArrayList<Uri> uris = intent.getParcelableArrayListExtra(Intent.EXTRA_STREAM);
        Uri single = intent.getParcelableExtra(Intent.EXTRA_STREAM);
        CharSequence text = intent.getCharSequenceExtra(Intent.EXTRA_TEXT);

        if (uris == null) uris = new ArrayList<>();
        if (single != null && uris.isEmpty()) uris.add(single);

        if (uris.isEmpty()) {
            byte[] raw = String.valueOf(text == null ? "" : text).getBytes(StandardCharsets.UTF_8);
            return new Incoming(raw, looksLikeUrl(new String(raw, StandardCharsets.UTF_8)) ? "SHARED_LINK_OR_TEXT" : "SHARED_TEXT");
        }

        if (uris.size() == 1) {
            try (InputStream in = getContentResolver().openInputStream(uris.get(0))) {
                if (in == null) throw new IllegalStateException("Cannot read shared file");
                return new Incoming(readAll(in), "SHARED_FILE");
            }
        }

        StringBuilder sb = new StringBuilder();
        if (text != null) sb.append("SHARED_TEXT:\n").append(text).append("\n\n");
        int i = 0;
        for (Uri uri : uris) {
            byte[] raw;
            try (InputStream in = getContentResolver().openInputStream(uri)) {
                if (in == null) continue;
                raw = readAll(in);
            }
            sb.append("===== FILE ").append(++i).append(" =====\n");
            sb.append("SHA256: ").append(Hashing.sha256(raw)).append("\n");
            sb.append(android.util.Base64.encodeToString(raw, android.util.Base64.NO_WRAP)).append("\n");
        }
        return new Incoming(sb.toString().getBytes(StandardCharsets.UTF_8), "SHARED_MULTI_FILE_ENVELOPE");
    }

    private void shareBundleToChatGpt() {
        if (currentJob == null) {
            refreshJob(false);
            toast("Load the job first.");
            return;
        }
        io.execute(() -> {
            try {
                File bundle = ResultStore.buildTextBundle(this, currentJob);
                main.post(() -> {
                    String pkg = AppBindings.packageFor(this, "chatgpt");
                    Intent intent = new Intent(Intent.ACTION_SEND);
                    intent.setType("text/plain");
                    Uri uri = fileUri(bundle);
                    intent.putExtra(Intent.EXTRA_STREAM, uri);
                    intent.putExtra(Intent.EXTRA_TEXT,
                            "Garden Relay completed " + currentJob.jobId + ". Exact reviewer results and SHA-256 receipts are attached.");
                    intent.setClipData(ClipData.newRawUri(bundle.getName(), uri));
                    intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
                    if (!pkg.trim().isEmpty()) {
                        intent.setPackage(pkg);
                        grantUriPermission(pkg, uri, Intent.FLAG_GRANT_READ_URI_PERMISSION);
                        if (prefs().getBoolean(PREF_AUTO_SEND, false)) {
                            prefs().edit()
                                    .putString(PREF_PENDING_SEND_PACKAGE, pkg)
                                    .putLong(PREF_PENDING_SEND_UNTIL, System.currentTimeMillis() + 120_000L)
                                    .apply();
                        }
                    }
                    try {
                        startActivity(pkg.trim().isEmpty() ? Intent.createChooser(intent, "Send Garden results") : intent);
                    } catch (ActivityNotFoundException e) {
                        toast("Bound ChatGPT app cannot receive this share; use Android Share chooser instead.");
                        intent.setPackage(null);
                        startActivity(Intent.createChooser(intent, "Send Garden results"));
                    }
                });
            } catch (Exception e) {
                main.post(() -> toast("Cannot build result bundle: " + e.getMessage()));
            }
        });
    }

    private void editJobUrl() {
        EditText edit = new EditText(this);
        edit.setSingleLine(false);
        edit.setText(prefs().getString(PREF_JOB_URL, JobClient.DEFAULT_JOB_URL));
        int pad = dp(18);
        edit.setPadding(pad, pad, pad, pad);

        new AlertDialog.Builder(this)
                .setTitle("Garden review job URL")
                .setMessage("Default is the public Garden mobile relay manifest. Change only when a review run gives you another frozen manifest URL.")
                .setView(edit)
                .setPositiveButton("Save", (d, w) -> {
                    prefs().edit().putString(PREF_JOB_URL, edit.getText().toString().trim()).apply();
                    refreshJob(false);
                })
                .setNeutralButton("Reset", (d, w) -> {
                    prefs().edit().remove(PREF_JOB_URL).apply();
                    refreshJob(false);
                })
                .setNegativeButton("Cancel", null)
                .show();
    }

    private static byte[] readAll(File file) throws Exception {
        try (InputStream in = new FileInputStream(file)) {
            return readAll(in);
        }
    }

    private static byte[] readAll(InputStream in) throws Exception {
        try (ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            byte[] buf = new byte[64 * 1024];
            int n;
            while ((n = in.read(buf)) > 0) out.write(buf, 0, n);
            return out.toByteArray();
        }
    }

    private static boolean looksLikeUrl(String value) {
        String s = value.trim().toLowerCase();
        return s.startsWith("https://") || s.startsWith("http://");
    }

    private static String safe(String value) {
        return value.replaceAll("[^A-Za-z0-9._-]", "_");
    }

    private String prettySlot(String slot) {
        switch (slot) {
            case "deepseek": return "DeepSeek";
            case "qwen": return "Qwen";
            case "gemini": return "Gemini";
            case "chatgpt": return "ChatGPT";
            default: return slot;
        }
    }

    private void status(String text) {
        statusView.setText(text);
    }

    private void toast(String text) {
        Toast.makeText(this, text, Toast.LENGTH_LONG).show();
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }

    private static final class Incoming {
        final byte[] bytes;
        final String kind;
        Incoming(byte[] bytes, String kind) {
            this.bytes = bytes;
            this.kind = kind;
        }
    }
}

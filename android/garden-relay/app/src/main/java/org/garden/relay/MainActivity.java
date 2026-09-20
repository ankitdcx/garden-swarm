package org.garden.relay;

import android.app.Activity;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.content.pm.PackageManager;
import android.content.pm.PackageInfo;
import android.content.Intent;
import java.util.ArrayList;
import java.util.List;
import rikka.shizuku.Shizuku;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import android.content.ComponentName;
import android.content.ServiceConnection;
import android.os.IBinder;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public final class MainActivity extends Activity {
    private static final String STATUS_URL =
            "https://raw.githubusercontent.com/ankitdcx/garden-swarm/chatgpt/garden-relay-android-20260920/relay/mobile/dashboard-status.json";

    private final ExecutorService io = Executors.newSingleThreadExecutor();
    private final Handler main = new Handler(Looper.getMainLooper());
    private LinearLayout board;
    private TextView header;
    private TextView note;
    private TextView bridge;
    private TextView discovery;
    private TextView calibration;
    private volatile boolean coordinateProbe = false;
    private volatile int coordinateAttempt = 0;
    private static final int SHIZUKU_REQ = 41;
    private final Shizuku.UserServiceArgs uiProbeArgs =
            new Shizuku.UserServiceArgs(new ComponentName("org.garden.reviewdashboard", UiProbeService.class.getName()))
                    .daemon(false).processNameSuffix("uiprobe").debuggable(true).version(12);
    private final ServiceConnection uiProbeConnection = new ServiceConnection() {
        @Override public void onServiceConnected(ComponentName name, IBinder binder) {
            io.execute(() -> {
                try {
                    IUiProbeService service = IUiProbeService.Stub.asInterface(binder);
                    String result;
                    if (coordinateProbe) {
                        android.util.DisplayMetrics dm = getResources().getDisplayMetrics();
                        int[][] offsets = new int[][]{{0,145},{0,210},{-180,145},{180,145}};
                        int i = Math.max(0, Math.min(coordinateAttempt, offsets.length-1));
                        int x = dm.widthPixels/2 + offsets[i][0];
                        int y = dm.heightPixels - offsets[i][1];
                        result = service.calibrateDeepSeekTapAt(x, y, dm.widthPixels, dm.heightPixels);
                        coordinateProbe = false;
                    } else {
                        result = service.probeDeepSeekInput();
                    }
                    main.post(() -> calibration.setText("DeepSeek input calibration: " +
                            (result.contains("total_nodes=0") ? "FAILED" : "STRUCTURE CAPTURED") +
                            "\n" + result + "\nNo text inserted; no message sent."));
                    try { Shizuku.unbindUserService(uiProbeArgs, this, true); } catch(Throwable ignored){}
                } catch (Throwable t) {
                    main.post(() -> calibration.setText("DeepSeek input calibration: FAILED — " +
                            t.getClass().getSimpleName() + ": " + String.valueOf(t.getMessage())));
                }
            });
        }
        @Override public void onServiceDisconnected(ComponentName name) {}
    };

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        buildUi();
        refresh();
        refreshShizuku();
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        io.shutdownNow();
    }

    private void buildUi() {
        ScrollView scroll = new ScrollView(this);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        int p = dp(18);
        root.setPadding(p,p,p,p);
        scroll.addView(root);

        TextView title = new TextView(this);
        title.setText("Garden Review Dashboard");
        title.setTextSize(27);
        root.addView(title);

        header = new TextView(this);
        header.setText("Loading review board…");
        header.setTextSize(15);
        header.setPadding(0,dp(10),0,dp(14));
        root.addView(header);

        bridge = new TextView(this);
        bridge.setText("Shizuku: checking…");
        bridge.setTextSize(16);
        bridge.setPadding(0,0,0,dp(10));
        root.addView(bridge);

        discovery = new TextView(this);
        discovery.setText("Reviewer apps: not probed");
        discovery.setTextSize(14);
        discovery.setPadding(0,0,0,dp(10));
        root.addView(discovery);

        calibration = new TextView(this);
        calibration.setText("DeepSeek calibration: NOT RUN");
        calibration.setTextSize(14);
        calibration.setPadding(0,0,0,dp(10));
        root.addView(calibration);

        Button coordinate = new Button(this);
        coordinate.setAllCaps(false);
        coordinate.setText("Calibrate DeepSeek composer tap (no type/send)");
        coordinate.setOnClickListener(v -> calibrateDeepSeekCoordinate());
        root.addView(coordinate);

        Button inputProbe = new Button(this);
        inputProbe.setAllCaps(false);
        inputProbe.setText("Calibrate DeepSeek input (no send)");
        inputProbe.setOnClickListener(v -> calibrateDeepSeekInput());
        root.addView(inputProbe);

        Button deepseekProbe = new Button(this);
        deepseekProbe.setAllCaps(false);
        deepseekProbe.setText("Calibrate DeepSeek launch");
        deepseekProbe.setOnClickListener(v -> calibrateDeepSeekLaunch());
        root.addView(deepseekProbe);

        Button probe = new Button(this);
        probe.setAllCaps(false);
        probe.setText("Probe installed reviewer apps");
        probe.setOnClickListener(v -> probeReviewerApps());
        root.addView(probe);

        Button authorize = new Button(this);
        authorize.setAllCaps(false);
        authorize.setText("Authorize Shizuku");
        authorize.setOnClickListener(v -> requestShizuku());
        root.addView(authorize);

        board = new LinearLayout(this);
        board.setOrientation(LinearLayout.VERTICAL);
        root.addView(board);

        Button refresh = new Button(this);
        refresh.setAllCaps(false);
        refresh.setText("Refresh status");
        refresh.setOnClickListener(v -> refresh());
        root.addView(refresh);

        note = new TextView(this);
        note.setTextSize(12);
        note.setPadding(0,dp(12),0,0);
        root.addView(note);

        setContentView(scroll);
    }

    private void refreshShizuku() {
        try {
            if (!Shizuku.pingBinder()) {
                bridge.setText("Shizuku: OFFLINE");
                return;
            }
            int uid = Shizuku.getUid();
            int perm = Shizuku.checkSelfPermission();
            bridge.setText("Shizuku: RUNNING (uid " + uid + ") — " +
                    (perm == PackageManager.PERMISSION_GRANTED ? "AUTHORIZED" : "NOT AUTHORIZED"));
        } catch (Throwable t) {
            bridge.setText("Shizuku: unavailable — " + t.getClass().getSimpleName());
        }
    }

    private void calibrateDeepSeekCoordinate() {
        if (!Shizuku.pingBinder() || Shizuku.checkSelfPermission() != PackageManager.PERMISSION_GRANTED) {
            calibration.setText("DeepSeek coordinate calibration: BLOCKED — Shizuku not authorized");
            return;
        }
        try {
            Intent launch = getPackageManager().getLaunchIntentForPackage("com.deepseek.chat");
            if (launch == null) { calibration.setText("DeepSeek coordinate calibration: BLOCKED — no launch activity"); return; }
            launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            startActivity(launch);
            coordinateAttempt = (coordinateAttempt + 1) % 4;
            coordinateProbe = true;
            calibration.setText("DeepSeek coordinate calibration: opening app; will tap composer region only…");
            main.postDelayed(() -> {
                try { Shizuku.bindUserService(uiProbeArgs, uiProbeConnection); }
                catch(Throwable t){ coordinateProbe=false; calibration.setText("DeepSeek coordinate calibration: FAILED — "+t.getClass().getSimpleName()); }
            }, 1800);
        } catch(Throwable t){ coordinateProbe=false; calibration.setText("DeepSeek coordinate calibration: FAILED — "+t.getClass().getSimpleName()); }
    }

    private void calibrateDeepSeekInput() {
        if (!Shizuku.pingBinder() || Shizuku.checkSelfPermission() != PackageManager.PERMISSION_GRANTED) {
            calibration.setText("DeepSeek input calibration: BLOCKED — Shizuku not authorized");
            return;
        }
        try {
            Intent launch = getPackageManager().getLaunchIntentForPackage("com.deepseek.chat");
            if (launch == null) {
                calibration.setText("DeepSeek input calibration: BLOCKED — no launch activity");
                return;
            }
            launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            startActivity(launch);
            calibration.setText("DeepSeek input calibration: opening app; waiting for UI…");
            main.postDelayed(() -> {
                try {
                    calibration.setText("DeepSeek structural calibration: probing redacted UI metadata…");
                    Shizuku.bindUserService(uiProbeArgs, uiProbeConnection);
                } catch (Throwable t) {
                    calibration.setText("DeepSeek input calibration: FAILED — " + t.getClass().getSimpleName());
                }
            }, 1800);
        } catch (Throwable t) {
            calibration.setText("DeepSeek input calibration: FAILED — " + t.getClass().getSimpleName());
        }
    }

    private void calibrateDeepSeekLaunch() {
        if (!Shizuku.pingBinder() || Shizuku.checkSelfPermission() != PackageManager.PERMISSION_GRANTED) {
            calibration.setText("DeepSeek calibration: BLOCKED — Shizuku not authorized");
            return;
        }
        try {
            PackageInfo pi = getPackageManager().getPackageInfo("com.deepseek.chat", 0);
            Intent launch = getPackageManager().getLaunchIntentForPackage("com.deepseek.chat");
            if (launch == null) {
                calibration.setText("DeepSeek calibration: BLOCKED — no launch activity");
                return;
            }
            launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            startActivity(launch);
            calibration.setText("DeepSeek calibration: LAUNCHED v" + pi.versionName +
                    " — no prompt inserted, no message sent");
        } catch (Throwable t) {
            calibration.setText("DeepSeek calibration: FAILED — " + t.getClass().getSimpleName());
        }
    }

    private void probeReviewerApps() {
        String[][] candidates = new String[][]{
                {"DeepSeek","com.deepseek.chat"},
                {"Gemini","com.google.android.apps.bard"},
                {"Claude","com.anthropic.claude"},
                {"Grok","ai.x.grok"}
        };
        List<String> rows = new ArrayList<>();
        for (String[] row : candidates) {
            try {
                PackageInfo pi = getPackageManager().getPackageInfo(row[1], 0);
                rows.add("✓ " + row[0] + " — " + row[1] + " — v" + pi.versionName);
            } catch (PackageManager.NameNotFoundException e) {
                rows.add("? " + row[0] + " — candidate package not found: " + row[1]);
            }
        }
        discovery.setText(String.join("\n", rows));
    }

    private void requestShizuku() {
        try {
            if (!Shizuku.pingBinder()) {
                bridge.setText("Shizuku: OFFLINE — start Shizuku first");
                return;
            }
            if (Shizuku.checkSelfPermission() == PackageManager.PERMISSION_GRANTED) {
                refreshShizuku();
                return;
            }
            Shizuku.requestPermission(SHIZUKU_REQ);
        } catch (Throwable t) {
            bridge.setText("Shizuku request failed: " + t.getClass().getSimpleName());
        }
    }

    private final Shizuku.OnRequestPermissionResultListener shizukuPermission =
            (requestCode, grantResult) -> {
                if (requestCode == SHIZUKU_REQ) runOnUiThread(this::refreshShizuku);
            };

    @Override
    protected void onResume() {
        super.onResume();
        Shizuku.addRequestPermissionResultListener(shizukuPermission);
        refreshShizuku();
    }

    @Override
    protected void onPause() {
        Shizuku.removeRequestPermissionResultListener(shizukuPermission);
        super.onPause();
    }

    private void refresh() {
        header.setText("Refreshing…");
        io.execute(() -> {
            try {
                String raw = get(STATUS_URL + "?t=" + System.currentTimeMillis());
                JSONObject root = new JSONObject(raw);
                main.post(() -> render(root));
            } catch (Exception e) {
                main.post(() -> header.setText("Status feed unavailable: " + e.getMessage()));
            }
        });
    }

    private void render(JSONObject root) {
        String project = root.optString("project","Garden review");
        String overall = root.optString("overall","UNKNOWN");
        String updated = root.optString("updated_at","");
        header.setText(project + "\nOverall: " + overall + "\nUpdated: " + updated);
        board.removeAllViews();
        JSONArray rows = root.optJSONArray("reviewers");
        if (rows != null) {
            for (int i=0;i<rows.length();i++) {
                JSONObject row = rows.optJSONObject(i);
                if (row == null) continue;
                TextView tv = new TextView(this);
                tv.setText(symbol(row.optString("status")) + "  " +
                        row.optString("label",row.optString("id")) + " — " +
                        row.optString("status","UNKNOWN"));
                tv.setTextSize(18);
                tv.setPadding(0,dp(9),0,dp(9));
                board.addView(tv);
            }
        }
        note.setText(root.optString("note","") +
                "\n\nThis dashboard does not read other apps, use Accessibility, or hold provider/GitHub credentials.");
    }

    private String symbol(String s) {
        switch (s) {
            case "COMPLETE": return "✓";
            case "RUNNING": return "●";
            case "BLOCKED": return "!";
            case "LOCKED": return "🔒";
            case "WAITING": return "○";
            default: return "·";
        }
    }

    private static String get(String url) throws Exception {
        HttpURLConnection c=(HttpURLConnection)new URL(url).openConnection();
        c.setConnectTimeout(15000); c.setReadTimeout(30000);
        c.setUseCaches(false);
        c.setRequestProperty("Cache-Control","no-cache, no-store, max-age=0");
        c.setRequestProperty("Pragma","no-cache");
        c.setRequestProperty("User-Agent","GardenReviewDashboard/0.4.1");
        int code=c.getResponseCode();
        if(code<200||code>=300) throw new IllegalStateException("HTTP "+code);
        try(InputStream in=c.getInputStream(); ByteArrayOutputStream out=new ByteArrayOutputStream()){
            byte[] b=new byte[16384]; int n;
            while((n=in.read(b))>0) out.write(b,0,n);
            return new String(out.toByteArray(), StandardCharsets.UTF_8);
        } finally { c.disconnect(); }
    }

    private int dp(int v){ return Math.round(v*getResources().getDisplayMetrics().density); }
}

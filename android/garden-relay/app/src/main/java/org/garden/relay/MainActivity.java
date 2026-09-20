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
import java.net.ServerSocket;
import java.net.Socket;
import java.io.OutputStream;
import java.util.concurrent.ConcurrentHashMap;
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
    private TextView sitesView;
    private volatile boolean coordinateProbe = false;
    private volatile int coordinateAttempt = 0;
    private volatile boolean localBridgeRunning = true;
    private final ConcurrentHashMap<String,String> browserCalibration = new ConcurrentHashMap<>();
    private final ConcurrentHashMap<String,String> browserJobs = new ConcurrentHashMap<>();
    private final ConcurrentHashMap<String,String> preparedJobs = new ConcurrentHashMap<>();
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
        startLocalBrowserBridge();
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        localBridgeRunning = false;
        io.shutdownNow();
    }

    private void startLocalBrowserBridge() {
        new Thread(() -> {
            try (ServerSocket server = new ServerSocket(17351, 8, java.net.InetAddress.getByName("127.0.0.1"))) {
                main.post(() -> bridge.setText("Browser bridge: READY — localhost 127.0.0.1:17351"));
                while (localBridgeRunning) {
                    try (Socket s = server.accept()) {
                        s.setSoTimeout(3000);
                        BufferedReader br = new BufferedReader(new InputStreamReader(s.getInputStream(), StandardCharsets.UTF_8));
                        String request = br.readLine();
                        if (request == null) continue;
                        int len=0; String line;
                        while ((line=br.readLine())!=null && !line.isEmpty()) {
                            if(line.toLowerCase().startsWith("content-length:")) len=Integer.parseInt(line.substring(15).trim());
                        }
                        char[] buf=new char[Math.max(0,Math.min(len,20000))]; int got=0,n;
                        while(got<buf.length && (n=br.read(buf,got,buf.length-got))>0) got+=n;
                        String body=new String(buf,0,got);
                        if(request.startsWith("GET /job/")) {
                            String provider=request.split(" ")[1].substring("/job/".length());
                            String payload=browserJobs.get(provider);
                            byte[] out=(payload==null?"{}":payload).getBytes(StandardCharsets.UTF_8);
                            OutputStream os=s.getOutputStream();
                            os.write(("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: "+out.length+"\r\nConnection: close\r\n\r\n").getBytes(StandardCharsets.UTF_8));
                            os.write(out); os.flush(); continue;
                        }
                        if(request.startsWith("POST /job/") && request.contains("/prepared")) {
                            String path=request.split(" ")[1];
                            String provider=path.substring("/job/".length(),path.length()-"/prepared".length());
                            preparedJobs.put(provider,body);
                            final String pp=provider;
                            main.post(() -> calibration.setText("Prompt prepared in Firefox: "+pp+"\nNo message submitted yet."));
                        }
                        if(request.startsWith("POST /calibration")) {
                            try {
                                JSONObject j=new JSONObject(body);
                                String provider=j.optString("provider","unknown");
                                browserCalibration.put(provider,body);
                                StringBuilder sv=new StringBuilder("Reviewers");
                                String[] ps={"deepseek","gemini","claude","grok"};
                                String[] names={"DeepSeek","Gemini","Claude","Grok"};
                                for(int qi=0;qi<ps.length;qi++){
                                    String raw=browserCalibration.get(ps[qi]);
                                    boolean ok=false;
                                    if(raw!=null) try { ok=new JSONObject(raw).optBoolean("composerFound",false); } catch(Throwable ignored2){}
                                    sv.append("\n").append(ok?"✓ ":"○ ").append(names[qi]).append(ok?" — connected":" — waiting");
                                }
                                final String siteStatus=sv.toString();
                                main.post(() -> sitesView.setText(siteStatus));
                                main.post(() -> calibration.setText("Browser calibration received: " + provider +
                                        "\ncomposerFound=" + j.optBoolean("composerFound",false) +
                                        "\n" + j.optJSONObject("composer")));
                            } catch(Throwable ignored){}
                        }
                        byte[] out="{\"ok\":true}".getBytes(StandardCharsets.UTF_8);
                        OutputStream os=s.getOutputStream();
                        os.write(("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: "+out.length+"\r\nConnection: close\r\n\r\n").getBytes(StandardCharsets.UTF_8));
                        os.write(out); os.flush();
                    } catch(Throwable ignored){}
                }
            } catch(Throwable t) {
                main.post(() -> bridge.setText("Browser bridge: FAILED — "+t.getClass().getSimpleName()));
            }
        },"GardenLocalBrowserBridge").start();
    }

    private void buildUi() {
        ScrollView scroll = new ScrollView(this);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        int p = dp(18);
        root.setPadding(p,p,p,p);
        scroll.addView(root);

        TextView title = new TextView(this);
        title.setText("Garden Browser Review");
        title.setTextSize(27);
        root.addView(title);

        TextView intro = new TextView(this);
        intro.setText("Free browser review bus — DeepSeek, Gemini, Claude and Grok");
        intro.setTextSize(15);
        intro.setPadding(0,dp(10),0,dp(18));
        root.addView(intro);

        bridge = new TextView(this);
        bridge.setText("Browser bridge: starting…");
        bridge.setTextSize(17);
        bridge.setPadding(0,0,0,dp(18));
        root.addView(bridge);

        calibration = new TextView(this);
        calibration.setText("Waiting for browser calibration…");
        calibration.setTextSize(15);
        calibration.setPadding(0,0,0,dp(18));
        root.addView(calibration);

        sitesView = new TextView(this);
        sitesView.setText("Reviewers\n○ DeepSeek — waiting\n○ Gemini — waiting\n○ Claude — waiting\n○ Grok — waiting");
        sitesView.setTextSize(17);
        sitesView.setPadding(0,0,0,dp(18));
        root.addView(sitesView);

        TextView help = new TextView(this);
        help.setText("Open a supported AI website in Firefox with the Garden userscript enabled. Composer calibration will appear here automatically. No Shizuku or Android app automation is used by this browser workflow.");
        help.setTextSize(14);
        root.addView(help);

        note = new TextView(this);
        note.setVisibility(android.view.View.GONE);
        root.addView(note);
        header = new TextView(this); header.setVisibility(android.view.View.GONE); root.addView(header);
        discovery = new TextView(this); discovery.setVisibility(android.view.View.GONE); root.addView(discovery);
        board = new LinearLayout(this); board.setVisibility(android.view.View.GONE); root.addView(board);

        setContentView(scroll);
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
                
                return;
            }
            Shizuku.requestPermission(SHIZUKU_REQ);
        } catch (Throwable t) {
            bridge.setText("Shizuku request failed: " + t.getClass().getSimpleName());
        }
    }

    private final Shizuku.OnRequestPermissionResultListener shizukuPermission =
            (requestCode, grantResult) -> {
                
            };

    @Override
    protected void onResume() {
        super.onResume();
        Shizuku.addRequestPermissionResultListener(shizukuPermission);
        
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

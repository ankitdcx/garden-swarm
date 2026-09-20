package org.garden.relay;

import android.app.Activity;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
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

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        buildUi();
        refresh();
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

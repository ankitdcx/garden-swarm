package org.garden.relay;

import android.content.Context;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

public final class JobClient {
    public static final String DEFAULT_JOB_URL =
            "https://raw.githubusercontent.com/ankitdcx/garden-swarm/main/relay/mobile/current-job.json";

    private JobClient() {}

    public static ReviewJob fetchJob(String url) throws Exception {
        byte[] raw = get(url);
        return ReviewJob.parse(new String(raw, StandardCharsets.UTF_8));
    }

    public static List<File> downloadAttachments(Context context, ReviewJob job, ReviewJob.Target target) throws Exception {
        File dir = new File(context.getCacheDir(), "jobs/" + safe(job.jobId) + "/" + safe(target.slot));
        if (!dir.exists() && !dir.mkdirs()) throw new IllegalStateException("Cannot create job cache directory");

        List<File> files = new ArrayList<>();
        for (ReviewJob.Attachment attachment : target.attachments) {
            File file = new File(dir, safe(attachment.filename));
            byte[] raw = get(attachment.url);
            String got = Hashing.sha256(raw);
            if (!attachment.sha256.isBlank() && !got.equalsIgnoreCase(attachment.sha256)) {
                throw new SecurityException("Attachment hash mismatch for " + attachment.filename);
            }
            try (FileOutputStream out = new FileOutputStream(file)) {
                out.write(raw);
            }
            files.add(file);
        }
        return files;
    }

    private static byte[] get(String urlString) throws Exception {
        HttpURLConnection conn = (HttpURLConnection) new URL(urlString).openConnection();
        conn.setConnectTimeout(15_000);
        conn.setReadTimeout(45_000);
        conn.setInstanceFollowRedirects(true);
        conn.setRequestProperty("User-Agent", "GardenRelayAndroid/0.1");
        int code = conn.getResponseCode();
        if (code < 200 || code >= 300) throw new IllegalStateException("HTTP " + code + " for " + urlString);
        try (InputStream in = conn.getInputStream(); ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            byte[] buf = new byte[64 * 1024];
            int n;
            while ((n = in.read(buf)) > 0) out.write(buf, 0, n);
            return out.toByteArray();
        } finally {
            conn.disconnect();
        }
    }

    private static String safe(String value) {
        return value.replaceAll("[^A-Za-z0-9._-]", "_");
    }
}

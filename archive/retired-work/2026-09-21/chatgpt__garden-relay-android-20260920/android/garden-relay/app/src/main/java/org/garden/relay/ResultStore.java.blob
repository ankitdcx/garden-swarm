package org.garden.relay;

import android.content.Context;
import android.util.Base64;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.nio.ByteBuffer;
import java.nio.CharBuffer;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.time.Instant;

public final class ResultStore {
    private ResultStore() {}

    public static File save(Context context, String jobId, String slot, byte[] raw, String kind) throws Exception {
        File dir = resultDir(context, jobId, slot);
        if (!dir.exists() && !dir.mkdirs()) throw new IllegalStateException("Cannot create result directory");

        File payload = new File(dir, "response.bin");
        try (FileOutputStream out = new FileOutputStream(payload)) {
            out.write(raw);
        }

        String sha = Hashing.sha256(raw);
        String receipt =
                "schema: GardenRelayResult/v1\n" +
                "job_id: " + jobId + "\n" +
                "slot: " + slot + "\n" +
                "kind: " + kind + "\n" +
                "bytes: " + raw.length + "\n" +
                "sha256: " + sha + "\n" +
                "received_utc: " + Instant.now().toString() + "\n";

        File receiptFile = new File(dir, "receipt.txt");
        try (FileOutputStream out = new FileOutputStream(receiptFile)) {
            out.write(receipt.getBytes(StandardCharsets.UTF_8));
        }
        return receiptFile;
    }

    public static boolean hasResult(Context context, String jobId, String slot) {
        return new File(resultDir(context, jobId, slot), "response.bin").isFile();
    }

    public static File buildTextBundle(Context context, ReviewJob job) throws Exception {
        File out = new File(context.getCacheDir(), "GardenRelay_" + safe(job.jobId) + "_results.txt");
        StringBuilder sb = new StringBuilder();
        sb.append("GARDEN RELAY RESULT BUNDLE\n");
        sb.append("schema: GardenRelayBundle/v1\n");
        sb.append("job_id: ").append(job.jobId).append("\n");
        sb.append("title: ").append(job.title).append("\n");
        sb.append("created_utc: ").append(Instant.now()).append("\n\n");

        for (ReviewJob.Target target : job.targets) {
            sb.append("===== REVIEWER ").append(target.slot.toUpperCase()).append(" =====\n");
            File payload = new File(resultDir(context, job.jobId, target.slot), "response.bin");
            if (!payload.isFile()) {
                sb.append("STATUS: MISSING\n\n");
                continue;
            }
            byte[] raw = readAll(payload);
            sb.append("STATUS: RECEIVED\n");
            sb.append("BYTES: ").append(raw.length).append("\n");
            sb.append("SHA256: ").append(Hashing.sha256(raw)).append("\n");
            String text = strictUtf8(raw);
            if (text != null) {
                sb.append("ENCODING: UTF-8\n");
                sb.append("--- RAW RESPONSE START ---\n");
                sb.append(text);
                if (!text.endsWith("\n")) sb.append("\n");
                sb.append("--- RAW RESPONSE END ---\n\n");
            } else {
                sb.append("ENCODING: BASE64_OF_ORIGINAL_BYTES\n");
                sb.append(Base64.encodeToString(raw, Base64.NO_WRAP)).append("\n\n");
            }
        }

        try (FileOutputStream stream = new FileOutputStream(out)) {
            stream.write(sb.toString().getBytes(StandardCharsets.UTF_8));
        }
        return out;
    }

    private static File resultDir(Context context, String jobId, String slot) {
        return new File(context.getFilesDir(), "results/" + safe(jobId) + "/" + safe(slot));
    }

    private static byte[] readAll(File file) throws Exception {
        try (FileInputStream in = new FileInputStream(file); ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            byte[] buf = new byte[64 * 1024];
            int n;
            while ((n = in.read(buf)) > 0) out.write(buf, 0, n);
            return out.toByteArray();
        }
    }

    private static String strictUtf8(byte[] raw) {
        try {
            CharBuffer cb = StandardCharsets.UTF_8.newDecoder()
                    .onMalformedInput(CodingErrorAction.REPORT)
                    .onUnmappableCharacter(CodingErrorAction.REPORT)
                    .decode(ByteBuffer.wrap(raw));
            return cb.toString();
        } catch (CharacterCodingException e) {
            return null;
        }
    }

    private static String safe(String value) {
        return value.replaceAll("[^A-Za-z0-9._-]", "_");
    }
}

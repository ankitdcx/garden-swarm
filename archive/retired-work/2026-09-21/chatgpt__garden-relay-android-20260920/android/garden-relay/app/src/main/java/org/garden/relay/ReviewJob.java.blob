package org.garden.relay;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.ArrayList;
import java.util.List;

public final class ReviewJob {
    public String schema = "";
    public String jobId = "";
    public String title = "";
    public String status = "";
    public final List<Target> targets = new ArrayList<>();

    public static final class Target {
        public String slot = "";
        public String displayName = "";
        public String prompt = "";
        public final List<Attachment> attachments = new ArrayList<>();
    }

    public static final class Attachment {
        public String filename = "";
        public String url = "";
        public String sha256 = "";
        public String mime = "text/plain";
    }

    public static ReviewJob parse(String json) throws Exception {
        JSONObject root = new JSONObject(json);
        ReviewJob job = new ReviewJob();
        job.schema = root.optString("schema", "");
        job.jobId = root.getString("job_id");
        job.title = root.optString("title", job.jobId);
        job.status = root.optString("status", "READY");

        JSONArray targets = root.optJSONArray("targets");
        if (targets == null) return job;

        for (int i = 0; i < targets.length(); i++) {
            JSONObject t = targets.getJSONObject(i);
            Target target = new Target();
            target.slot = t.getString("slot").toLowerCase();
            target.displayName = t.optString("display_name", target.slot);
            target.prompt = t.optString("prompt", "");

            JSONArray attachments = t.optJSONArray("attachments");
            if (attachments != null) {
                for (int j = 0; j < attachments.length(); j++) {
                    JSONObject a = attachments.getJSONObject(j);
                    Attachment attachment = new Attachment();
                    attachment.filename = a.getString("filename");
                    attachment.url = a.getString("url");
                    attachment.sha256 = a.optString("sha256", "");
                    attachment.mime = a.optString("mime", "text/plain");
                    target.attachments.add(attachment);
                }
            }
            job.targets.add(target);
        }
        return job;
    }

    public Target targetFor(String slot) {
        for (Target target : targets) {
            if (target.slot.equals(slot)) return target;
        }
        return null;
    }
}

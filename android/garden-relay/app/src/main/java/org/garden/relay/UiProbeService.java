package org.garden.relay;

import android.content.Context;
import android.os.RemoteException;
import android.system.Os;
import androidx.annotation.Keep;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public final class UiProbeService extends IUiProbeService.Stub {
    public UiProbeService() {}
    @Keep public UiProbeService(Context context) {}

    @Override public void destroy() { System.exit(0); }

    @Override public String calibrateDeepSeekTapAt(int x, int y, int width, int height) throws RemoteException {
        try {
            if (width < 300 || height < 600 || x < 0 || y < 0 || x >= width || y >= height)
                return "invalid_tap=" + x + "," + y + "; display=" + width + "x" + height;
            Process p = new ProcessBuilder("input","tap",String.valueOf(x),String.valueOf(y)).start();
            int rc = p.waitFor();
            return "uid=" + Os.getuid() + "; tap_rc=" + rc + "; display=" + width + "x" + height +
                    "; tap=" + x + "," + y + "; text_inserted=false; message_sent=false";
        } catch (Throwable t) {
            throw new RemoteException(t.getClass().getSimpleName()+": "+String.valueOf(t.getMessage()));
        }
    }

    @Override public String calibrateDeepSeekTap(int width, int height) throws RemoteException {
        try {
            if (width < 300 || height < 600) return "invalid_display=" + width + "x" + height;
            int x = width / 2;
            int y = Math.max(1, height - Math.max(120, height / 12));
            Process p = new ProcessBuilder("input","tap",String.valueOf(x),String.valueOf(y)).start();
            int rc = p.waitFor();
            return "uid=" + Os.getuid() + "; tap_rc=" + rc + "; display=" + width + "x" + height +
                    "; tap=" + x + "," + y + "; text_inserted=false; message_sent=false";
        } catch (Throwable t) {
            throw new RemoteException(t.getClass().getSimpleName()+": "+String.valueOf(t.getMessage()));
        }
    }

    @Override public String probeDeepSeekInput() throws RemoteException {
        Process p = null;
        try {
            p = new ProcessBuilder("sh","-c",
                    "uiautomator dump /data/local/tmp/garden_deepseek_ui.xml >/dev/null 2>&1; cat /data/local/tmp/garden_deepseek_ui.xml; rm -f /data/local/tmp/garden_deepseek_ui.xml")
                    .redirectErrorStream(true).start();
            StringBuilder sb = new StringBuilder();
            try (BufferedReader br = new BufferedReader(new InputStreamReader(p.getInputStream()))) {
                String line; while ((line = br.readLine()) != null) sb.append(line);
            }
            int rc = p.waitFor();
            String xml = sb.toString();
            Pattern node = Pattern.compile("<node[^>]*/?>");
            Matcher m = node.matcher(xml);
            int total=0, clickable=0, focusable=0, enabled=0;
            StringBuilder candidates = new StringBuilder();
            while(m.find()){
                total++;
                String n=m.group();
                boolean click=n.contains("clickable=\\\"true\\\"");
                boolean focus=n.contains("focusable=\\\"true\\\"");
                boolean en=n.contains("enabled=\\\"true\\\"");
                if(click) clickable++; if(focus) focusable++; if(en) enabled++;
                if ((click || focus) && candidates.length() < 5000) {
                    String safe=n.replaceAll("text=\\\"[^\\\"]*\\\"","text=\\\"[redacted]\\\"")
                            .replaceAll("content-desc=\\\"[^\\\"]*\\\"","content-desc=\\\"[redacted]\\\"")
                            .replaceAll("hint=\\\"[^\\\"]*\\\"","hint=\\\"[redacted]\\\"");
                    candidates.append("\\n").append(safe);
                }
            }
            return "uid="+Os.getuid()+"; rc="+rc+"; total_nodes="+total+
                    "; clickable="+clickable+"; focusable="+focusable+"; enabled="+enabled+
                    "; structural_candidates="+candidates.toString();
        } catch (Throwable t) {
            throw new RemoteException(t.getClass().getSimpleName()+": "+String.valueOf(t.getMessage()));
        } finally {
            try { new ProcessBuilder("rm","-f","/data/local/tmp/garden_deepseek_ui.xml").start().waitFor(); } catch(Throwable ignored){}
            if(p!=null) p.destroy();
        }
    }
}

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
            Pattern edit = Pattern.compile("<node[^>]*(?:class=\\\"android\\.widget\\.EditText\\\"|editable=\\\"true\\\")[^>]*>");
            Matcher m = edit.matcher(xml);
            int count=0; String first="";
            while(m.find()){ count++; if(first.isEmpty()) first=m.group(); }
            first=first.replaceAll("text=\\\"[^\\\"]*\\\"","text=\\\"[redacted]\\\"")
                    .replaceAll("content-desc=\\\"[^\\\"]*\\\"","content-desc=\\\"[redacted]\\\"");
            return "uid="+Os.getuid()+"; rc="+rc+"; editable_nodes="+count+(first.isEmpty()?"":"; first="+first);
        } catch (Throwable t) {
            throw new RemoteException(t.getClass().getSimpleName()+": "+String.valueOf(t.getMessage()));
        } finally {
            try { new ProcessBuilder("rm","-f","/data/local/tmp/garden_deepseek_ui.xml").start().waitFor(); } catch(Throwable ignored){}
            if(p!=null) p.destroy();
        }
    }
}

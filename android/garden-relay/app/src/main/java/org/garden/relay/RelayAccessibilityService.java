package org.garden.relay;

import android.accessibilityservice.AccessibilityService;
import android.content.SharedPreferences;
import android.os.SystemClock;
import android.view.accessibility.AccessibilityEvent;
import android.view.accessibility.AccessibilityNodeInfo;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

public final class RelayAccessibilityService extends AccessibilityService {
    private static final String PREF_PENDING_SEND_PACKAGE = "pending_send_package";
    private static final String PREF_PENDING_SEND_UNTIL = "pending_send_until";

    @Override
    public void onAccessibilityEvent(AccessibilityEvent event) {
        if (event == null || event.getPackageName() == null) return;

        SharedPreferences prefs = AppBindings.prefs(this);
        String pendingPackage = prefs.getString(PREF_PENDING_SEND_PACKAGE, "");
        long until = prefs.getLong(PREF_PENDING_SEND_UNTIL, 0L);
        String eventPackage = String.valueOf(event.getPackageName());

        if (pendingPackage.trim().isEmpty()) return;
        if (System.currentTimeMillis() > until) {
            clearPending(prefs);
            return;
        }
        if (!pendingPackage.equals(eventPackage)) return;
        if (!AppBindings.boundPackages(this).contains(eventPackage)) return;

        AccessibilityNodeInfo root = getRootInActiveWindow();
        if (root == null) return;

        List<AccessibilityNodeInfo> candidates = new ArrayList<>();
        collectSafeSendButtons(root, candidates, 0);

        // Fail closed: never guess among multiple possible buttons.
        if (candidates.size() != 1) return;

        AccessibilityNodeInfo node = candidates.get(0);
        if (node.isEnabled() && node.isClickable()) {
            boolean clicked = node.performAction(AccessibilityNodeInfo.ACTION_CLICK);
            if (clicked) clearPending(prefs);
        }
    }

    private void collectSafeSendButtons(AccessibilityNodeInfo node, List<AccessibilityNodeInfo> out, int depth) {
        if (node == null || depth > 40 || out.size() > 2) return;

        String text = normalized(node.getText());
        String desc = normalized(node.getContentDescription());

        if (node.isClickable() && node.isEnabled() && (isSafeSendLabel(text) || isSafeSendLabel(desc))) {
            out.add(node);
        }

        for (int i = 0; i < node.getChildCount(); i++) {
            collectSafeSendButtons(node.getChild(i), out, depth + 1);
        }
    }

    private boolean isSafeSendLabel(String value) {
        if (value.isEmpty()) return false;
        return value.equals("send")
                || value.equals("send message")
                || value.equals("submit")
                || value.equals("send prompt")
                || value.equals("发送")
                || value.equals("送信")
                || value.equals("भेजें");
    }

    private String normalized(CharSequence value) {
        if (value == null) return "";
        return value.toString().trim().toLowerCase(Locale.ROOT);
    }

    private void clearPending(SharedPreferences prefs) {
        prefs.edit().remove(PREF_PENDING_SEND_PACKAGE).remove(PREF_PENDING_SEND_UNTIL).apply();
    }

    @Override
    public void onInterrupt() {
        // No persistent work. The helper is intentionally one-shot.
    }
}

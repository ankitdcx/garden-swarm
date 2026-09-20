package org.garden.relay;

import android.content.Context;
import android.content.SharedPreferences;

import java.util.HashSet;
import java.util.Set;

public final class AppBindings {
    public static final String PREFS = "garden_relay";
    public static final String[] SLOTS = {"deepseek", "gemini", "claude", "grok", "chatgpt"};

    private AppBindings() {}

    public static SharedPreferences prefs(Context context) {
        return context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    public static String packageFor(Context context, String slot) {
        return prefs(context).getString("package_" + slot, "");
    }

    public static void bind(Context context, String slot, String packageName, String label) {
        prefs(context).edit()
                .putString("package_" + slot, packageName)
                .putString("label_" + slot, label)
                .apply();
    }

    public static String labelFor(Context context, String slot) {
        return prefs(context).getString("label_" + slot, "");
    }

    public static Set<String> boundPackages(Context context) {
        Set<String> out = new HashSet<>();
        for (String slot : SLOTS) {
            String value = packageFor(context, slot);
            if (!value.trim().isEmpty()) out.add(value);
        }
        return out;
    }
}

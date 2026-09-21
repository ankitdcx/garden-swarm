# Garden Android Consumer-App Automation Bridge

Status: NONCANONICAL PROTOTYPE PLAN

Goal: use the user's installed consumer apps (DeepSeek, Gemini, Claude, Grok) and their free accounts for fast independent Garden reviews, without routing normal phone reviews through OpenRouter.

## Selected mechanism

Use Shizuku as the one-time privilege bridge on Android 11+.

Shizuku is a user-installed open-source bridge that can expose ADB/shell-level Android APIs to an explicitly authorized app. It can be started on-device using Android Wireless debugging. It is not root and it must be restarted after reboot on non-rooted devices.

Garden Review Dashboard will request Shizuku permission explicitly. It must not silently acquire it.

## Why this replaces Accessibility

The earlier Accessibility approach was rejected after Play Protect flagged the capability as sensitive. The bridge must not request Android Accessibility.

The automation adapter may use only the narrow operations required for the review job:
- launch a specifically bound reviewer package;
- inject the frozen prompt through shell/input or supported intent;
- trigger a bounded send action through deterministic app-specific coordinates/selectors only after adapter calibration;
- inspect the foreground UI hierarchy through shell tooling where Android permits it;
- wait for stable response text;
- extract only the active review conversation response;
- hash/store the response and advance the job.

It must not scan unrelated apps, notifications, contacts, messages, passwords, financial apps, or background personal content.

## Reviewer adapters

Adapters are separate and fail closed:
- DeepSeek
- Gemini
- Claude
- Grok

Each adapter records:
- package name;
- app version last qualified;
- prompt-input strategy;
- send strategy;
- response-completion detector;
- response extraction strategy;
- calibration fingerprint;
- last qualification receipt.

An app update invalidates the adapter until a probe succeeds.

## Parallelism

Android can only have one normal foreground interaction at a time. "Parallel" therefore means rapid fan-out:
1. open reviewer A and submit;
2. open reviewer B and submit;
3. open reviewer C and submit;
4. open reviewer D and submit;
5. poll each conversation in rotation until complete.

The models compute remotely at the same time after dispatch.

## Evidence rule

Dashboard RUNNING requires a real dispatch receipt containing reviewer, package, job hash, prompt hash, and dispatch time.
COMPLETE requires extracted response bytes plus SHA-256.
No synthetic state is allowed outside an explicitly labelled MOCK mode.

## One-time human setup

1. Install official Shizuku.
2. Enable Android Developer options and Wireless debugging.
3. Pair/start Shizuku.
4. Grant Garden Review Dashboard permission in Shizuku.
5. Run one calibration probe per installed reviewer app.

After reboot, non-rooted Shizuku normally needs to be started again. The dashboard should detect this and show BRIDGE_OFFLINE rather than pretending jobs can run.

## ColorOS note

Shizuku's official setup documentation notes that ColorOS may require disabling "Permission monitoring" in Developer options when ADB permissions are restricted. Only do this if Shizuku itself reports the ColorOS limitation.

## Security boundary

No Garden semantic authority follows from UI automation, model output, successful dispatch, response extraction, or reviewer agreement.

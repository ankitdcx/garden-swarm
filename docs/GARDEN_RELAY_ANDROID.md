# Garden Relay Android — phone-side model review bus

Status: NONCANONICAL OPERATIONAL PROTOTYPE

## Purpose

Garden Relay reduces the user's manual work when a Garden review uses separate phone apps such as DeepSeek, Qwen,
Gemini and ChatGPT.

It does not make those providers trusted, does not give any model authority, and does not change Garden semantics.

## One-time setup

1. Install the Garden Relay APK.
2. Open Garden Relay.
3. Tap each binding button once:
   - DeepSeek -> choose the installed DeepSeek app.
   - Qwen -> choose the installed Qwen app.
   - Gemini -> choose the installed Gemini app.
   - ChatGPT -> choose the installed ChatGPT app.
4. Optional: enable the one-shot Accessibility Send helper in Android Accessibility settings.
   The helper is not required. It is deliberately narrow and fail-closed.

Package names are not hardcoded. Garden Relay queries Android for apps that expose a compatible Share target and stores
the package chosen by the user.

## Normal review flow

1. Garden Relay fetches the current frozen mobile job manifest from:
   https://raw.githubusercontent.com/ankitdcx/garden-swarm/main/relay/mobile/current-job.json
2. It verifies every declared SHA-256 attachment before sending anything.
3. Tap "Run next reviewer".
4. Relay opens the correct bound app with the frozen prompt and packet/source attachment(s).
5. If the optional one-shot Accessibility helper is enabled, it will tap Send only when:
   - the current package is exactly the armed bound package;
   - the arming window has not expired;
   - exactly one enabled/clickable node has a strict Send/Submit label.
   Otherwise it does nothing.
6. When the model finishes, use that app's Share function and select Garden Relay.
   Relay stores the exact shared text/file/link, hashes it, and automatically advances to the next reviewer when enabled.
7. After all external reviewers return, tap "Share completed bundle to ChatGPT".
   Relay produces one plain UTF-8 result bundle containing the exact raw text responses (or Base64 for non-text bytes)
   plus SHA-256 hashes and shares it directly to the bound ChatGPT app.

The only recurring human action intended in the common path is sharing the completed model answer back to Garden Relay
when the source app does not expose an automatable return path.

## Why Share intents

Android Share is a stable OS boundary. It is substantially less brittle than coordinate-based UI automation and does not
require reading the user's clipboard, screenshots, notifications, passwords, or hidden app storage.

If a target app cannot receive SEND_MULTIPLE, Relay falls back to one combined text attachment.

## Privacy/safety boundary

Garden Relay v0.1:
- does not read the clipboard;
- does not record the screen;
- does not monitor notifications;
- does not request contacts/location/microphone/camera;
- does not store provider passwords/API keys;
- does not use QUERY_ALL_PACKAGES;
- does not continuously scrape Accessibility content;
- does not upload result content to a server;
- stores returned raw review payloads only in app-private storage until the user shares the resulting bundle.

Accessibility is optional. It is armed for one selected package for at most two minutes and clears after one successful
Send click or timeout. If multiple matching buttons exist it fails closed.

## Current limitation

Android apps choose what they expose through the Share Sheet. Garden Relay can discover and use those declared
interfaces, but it cannot force a provider app to accept multiple files or return a response programmatically.

Therefore v0.1 deliberately uses:
- automatic target launch/input handoff where the app allows it;
- one-shot Send assistance where safely identifiable;
- the provider's normal Share command for result return;
- one final share to ChatGPT.

A future paired bridge can remove the final ChatGPT share step, but it should use a narrow device identity/token rather
than a general GitHub credential on the phone.

## Build

The PR workflow .github/workflows/garden-relay-android.yml builds:

    android/garden-relay/app/build/outputs/apk/debug/app-debug.apk

The workflow artifact is named:

    garden-relay-debug-apk

No release signing key is committed to the repository.

## Review-job manifest

See relay/mobile/job-schema-example.json.

A job target may contain multiple text/source attachments. Every attachment may declare a SHA-256; mismatch blocks the
handoff.

Slots currently recognized:
- deepseek
- qwen
- gemini
- chatgpt (result destination; not automatically treated as an external reviewer)

## Authority boundary

The relay is transport only.

A successful transfer, hash match, provider response, or model agreement does not create:
- Garden truth;
- Proof;
- semantic admission;
- implementation certification;
- human authority;
- deployment permission.

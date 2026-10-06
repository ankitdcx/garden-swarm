# AI Council userscript (Android Firefox)
Primary installation route: Firefox Android + Violentmonkey (or Tampermonkey).

1. Install Violentmonkey from Mozilla Add-ons for Firefox Android.
2. Open this repository's raw ai-council.user.js URL in Firefox; Violentmonkey should offer to install it. If not, create a new script in Violentmonkey and paste the file.
3. Open and log into ChatGPT, Gemini, Claude, Grok and/or DeepSeek in separate Firefox tabs.
4. Keep those tabs loaded. On any supported tab use the floating AI Council panel.
5. ASK ALL broadcasts a shared job through userscript storage. Each loaded AI tab independently submits the question and stores its response.
6. CROSS-CHECK broadcasts the collected anonymized answers.
7. FINAL asks every loaded tab for a synthesis; the last completed final response is displayed.
8. STOP prevents response polling from continuing.

No API keys and no OpenRouter. This is DOM automation and a website UI update may require updating that site's selectors.

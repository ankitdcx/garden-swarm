# Garden parallel review controller

Status: NONCANONICAL OPERATIONAL POLICY

Active phone reviewers: DeepSeek, Gemini, Claude, Grok.
Qwen: disabled.

## Automated API lane

For PUBLIC Garden review packets:
- fan out up to four independent reviewer calls concurrently;
- give every reviewer the same frozen packet plus its own specialist role;
- never include peer answers during the blind round;
- wait up to 30 minutes for the round;
- check completion every 30 seconds only when a provider has no callback/event;
- retry a transport failure at most once after 60 seconds;
- do not retry substantive UNKNOWN/BLOCK answers merely to obtain a different opinion;
- hash and freeze every result separately;
- prefer at least four distinct families; require at least three for an ordinary complete board;
- if fewer than three succeed, mark the board incomplete rather than pretending it completed;
- majority vote is never an admission rule.

Prefer OpenRouter free routes for unattended routine review. Paid/frontier use remains governed by the separate budget
policy.

## Phone-app lane

Garden Relay supports DeepSeek, Gemini, Claude and Grok as optional consumer-app cross-checks.

Consumer apps cannot be made fully unattended without a provider-supported API/callback or sensitive cross-app UI
automation. Garden Relay does not use Accessibility.

## Event flow

frozen eligible review event
-> concurrent blind fan-out
-> bounded wait/poll
-> exact result freeze/hashes
-> result bundle
-> lead reconciliation
-> integrated candidate
-> separate verifier

## Human interruptions

Routine technical review should not interrupt the human.

Escalate only:
- constitutional/rights choices;
- major architecture or original-intent ambiguity;
- one-time provider/account setup;
- budget authorization outside configured limits;
- a requested consumer-app-only review that has no supported automation interface.

This policy creates no Garden semantic authority.

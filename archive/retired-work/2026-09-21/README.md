# Retired Garden work recovery — 2026-09-21

This directory preserves exact Git blobs from branches explicitly retired by the user after asking to keep only the latest v15.10/v15.11 lines, with GCSC treated as v15.10 work.

The recovery is archival only:
- original live paths were not restored;
- current v15.10/GCSC and v15.11 work were not overwritten;
- each batch file records the retired branch head SHA, comparison base, PR number where available, original path, archived path, and exact blob SHA;
- canonical effect: NONE;
- authority effect: NONE.

Recovered retired public branch heads:
- 586d871fa8cfed06ee21556ed7d9cea6ab6033c3 — android app automation bridge
- ac3f86766a8518728c36de8ecd8ffb4a7b5c349e — council prior-art review
- 0c49047283b2498e9015d95909d549a380be878d — Firefox review controller
- 1bd50d886cfef9920a1a244df02c5ab84b34d943 — Garden Relay Android
- 8e254fa3ab9a049a83cffcef15badaf61b345e06 — GROUP_REVIEW operational closure
- b8cfcaf2afa543b74cc25e294f22b9b71b05c049 — v15.9 documentation/review rebuild
- 0544dd7471ed6cc53c566f270fdcf526ac5beb18 — v15.10/v15.11 materialization current-main
- e829311365c006e9723414bcd4d39e24c8943678 — v15.10/v15.11 standalone release
- 78f976464ee9f4746317b8ca417ef9221f4eeb52 — v15.11 final retention status
- c45d7b4be50d699cf957db0153ad519f75258a45 — v15.11 whole-system audit

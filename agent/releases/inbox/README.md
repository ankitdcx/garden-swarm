# One-use standalone release inbox

Upload exactly one file to this directory on branch:

`chatgpt/v1510-v1511-standalone-release-20260920`

Required filename:

`Garden_v15.10_STANDALONE_NO_LOSS_CANDIDATE_2026-09-20.zip`

Required SHA-256:

`9af4f13415c05c94c693ef9720c1917801cffa0ead86ff1b06895291d089561b`

The branch workflow will:

1. verify the ZIP hash;
2. verify every v15.10 primary source against the committed release manifest;
3. verify Book, Technical and History against the already-committed readable source representation;
4. extract only the exact UTF-8 Catalogue and semantic-retention disposition into the current release content store;
5. prove deterministic v15.10 and v15.11 reconstruction;
6. commit the verified content;
7. delete the uploaded ZIP transport file.

The ZIP is transport only and never becomes a controlling Garden source.

Do not upload a renamed, recompressed or regenerated package under the required filename. Hash mismatch fails closed.

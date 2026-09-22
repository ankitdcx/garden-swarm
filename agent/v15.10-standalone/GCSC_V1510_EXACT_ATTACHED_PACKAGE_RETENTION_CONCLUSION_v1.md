# Exact attached v15.10 package — retention conclusion

The 19 September three-document package removes the previous source blocker.

## Verified locally
- ZIP manifest hashes match all three current design documents and README.
- Technical Core extracted from Technical Design hashes exactly to the declared Technical SHA-256.
- The readable Catalogue contains exactly 19,921 canonical machine records.
- Every record hash validates under GardenCanonicalEncoding/v3.
- Canonical record ordering/root reconstruction reproduces Catalogue root d41c44fc28e5c43c5532846174ef46abca0f9b85c70f64813c481fb4f0856c9a.
- Catalogue embeds five exact v15.9 SOURCE_BLOBs.
- Running the extracted Technical Core's reconstruct_source() over the recovered machine Catalogue returns PASS for all five embedded predecessor sources.
- Stratum 0 reproduces 19,921 nodes; bounded seed-local generation produces 21,132 additional nodes; total = declared 41,053 graph nodes.

## Semantic meaning
The current build explicitly recognizes no semantic admissions and allows no predecessor elision.
All structured interpretation remains SOURCE_ONLY.
INTERPRETATION_DEBT remains OPEN_BOUNDED_DEBT with 2,660 predecessor semantic leaves and zero verified-equivalent elisions.

Therefore the current v15.10 package is lossless with respect to v15.9 by retaining exact predecessor source as controlling semantic fallback. This is stronger than relying on the seven Design Forms to reproduce every predecessor statement.

It is NOT yet a fully structured replacement of v15.9. GCSC should now be used to reduce the 2,660 SOURCE_ONLY semantic leaves by proving accepted structured equivalence/refinement one unit at a time.

## From-zero rebuild
A from-zero v15.10 is technically possible, but it would throw away the strongest current anti-loss property unless it is built as a successor candidate and proven equivalent against this exact package. The attached package should therefore remain the retention oracle/baseline while any cleaner from-zero successor is developed.

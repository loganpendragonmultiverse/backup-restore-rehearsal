# Changelog

## 0.1.0 — 2026-10-15

- Added one explicitly selected ZIP backup plus a supplied schema-1 SHA-256 manifest. Inspect the entire selected archive and verify its file set and hashes before extraction; restore only to a random newly created disposable child under an explicitly selected parent; rehash every restored file before reporting success.
- Add CRC-corruption, inclusive size/count boundaries, reparse-attribute and native Windows junction regression fixtures.
- Added original implementation, synthetic fixtures, safety regression tests, usage documentation and MIT licensing.
- Release preparation includes corrected privacy/support wording and tag-build checksum packaging. Publication remains gated; this changelog alone does not establish a public release.

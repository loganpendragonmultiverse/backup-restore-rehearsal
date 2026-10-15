# Changelog

## 0.1.0 — 2026-10-15

- Added one explicitly selected ZIP backup plus a supplied schema-1 SHA-256 manifest. Inspect the entire selected archive and verify its file set and hashes before extraction; restore only to a random newly created disposable child under an explicitly selected parent; rehash every restored file before reporting success.
- Add CRC-corruption, inclusive size/count boundaries, reparse-attribute and native Windows junction regression fixtures.
- Added synthetic examples, regression tests, usage documentation and MIT licensing.
- Added version-checked release packaging with SHA-256 checksums.

# Testing

Tests use synthetic archives only. They exercise exact restored hashes, distinct disposable targets, source and existing-data preservation, traversal/drive/UNC/ADS names, Unicode and case collisions, reserved Windows names, symlinks, duplicate members, duplicate manifest keys, directory/file collisions, high compression ratios, corrupt archives, manifest mismatches, and explicit review.

`python -m pip install -e ".[dev]"`; `ruff format --check .`; `ruff check .`; `mypy src`; `pytest`; `python -m build`.

Exact execution results and environment evidence are supplied with the RC bundle. CI definitions are not proof of completed remote CI. Public release remains gated on successful remote checks and maintainer security review.

## Candidate evidence — 2026-10-15

Windows Python 3.14.3: 33 passed, one symlink-creation fixture skipped due OS permission; branch-aware coverage 92.22%; Ruff format/lint and strict mypy passed; wheel and source distribution built.

Linux container and remote CI results are recorded in the release-candidate evidence packet. macOS and Firefox remain unverified unless the remote checks explicitly establish them. No real backup or private browsing was used.

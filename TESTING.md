# Testing

Install development tools with `python -m pip install -e ".[dev]"`. Run `ruff format --check .`, `ruff check .`, `mypy src`, `pytest`, `python -m build` and `python -m pip_audit .`.

Synthetic ZIP fixtures cover verified restores, manifest mismatches, CRC corruption, file and archive size limits, expansion ratio, member counts, path depth, traversal, reserved names, collisions, encrypted or unsupported entries, symlink and reparse metadata, and refusal to use unsafe output parents. Tests never read real backups.

## Verified environments

On 2026-10-15, Linux passed 38 tests with one platform skip and 94.44% branch-aware coverage. Formatting, lint, strict typing, dependency audit and package builds passed. GitHub CI also passed on Python 3.11 across Windows, macOS and Linux. CodeQL analysis and result upload passed.

Native Windows testing passed 38 tests with one skip. `test_native_windows_junction_output_parent_is_rejected` passed: a newly created junction was refused as an output parent, and no restore directory appeared in its target. `test_selected_symlink_parent_rejected` was skipped because the account could not create an OS symlink. Linux skips the native Windows junction test by platform. Archive symlink-member rejection is tested separately.

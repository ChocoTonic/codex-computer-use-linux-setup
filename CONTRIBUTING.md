# Contributing

Keep this repository focused on repeatable Codex setup for the documented X11 environment. Credit upstream backend work explicitly.

## Validate changes

Run unit tests and patch checks before submitting a pull request. For launcher, input, or accessibility changes, also run the desktop suite on a disposable X11 session. Document which environment you tested.

## Update the upstream pin

1. Review the upstream release and license.
2. Update the commit and version in `scripts/setup.py`, CI, and documentation.
3. Check whether upstream already contains the drag fix. Remove or adapt the patch as appropriate.
4. Build against the pinned lockfile on Ubuntu 22.04.
5. Run upstream's MCP contract check and this repository's configuration and desktop checks.
6. Record any changed requirements and compatibility limits.

Preserve upstream copyright notices when modifying or redistributing derived code. Use upstream issues or pull requests for backend improvements that benefit all clients; this repository does not automatically submit changes upstream.

## Keep private data out of commits

Do not commit Codex authentication files, home-directory snapshots, personal config files, raw desktop logs, screenshots, or SSH keys. Use generic paths in examples and publish redacted summaries of test results.

# Security

The connector can observe and control your logged-in desktop. Install it for a user and desktop you intend Codex to control. This setup does not isolate applications or change Codex's approval policy.

Builds fetch a pinned upstream source commit and its locked Rust dependencies. Review the patch before installing. Reused binaries require an explicit checksum from a trusted source.

The installer backs up changed files in a private state directory. Verification results can contain desktop metadata or screen contents. Keep those directories private and review any excerpts before sharing.

For backend vulnerabilities, use the upstream project's security reporting process. For installer vulnerabilities, contact the repository owner through GitHub. Avoid posting credentials, screenshots of private content, or exploitable private-system details in public issues.

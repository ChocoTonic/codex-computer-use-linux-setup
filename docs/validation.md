# Validation

## Original VM verification

On October 26, 2026, the locally built backend was transferred between two Lubuntu Hyper-V Generation 2 VMs. Both used Ubuntu 22.04.5 LTS, x86-64, GLIBC 2.35, LXQt/Openbox, and X11.

The transferred backend's SHA-256 checksum matched on both machines:

```text
ff827a607286e70e3f6cc26c817c4cbc03c09db5d2b78adea5a5ba8383206073
```

This checksum identifies that original build. Later compiler versions or build environments can produce different binaries. No binary is distributed in this repository.

The destination passed these 18 checks:

1. MCP tool discovery.
2. Accessibility enabled.
3. Window backend ready.
4. Input backend ready.
5. Disposable fixture started.
6. Fixture window discovered.
7. Exact window focus.
8. Scoped semantic tree.
9. Desktop screenshot.
10. Window screenshot.
11. Unicode semantic text write with readback.
12. Semantic button activation with readback.
13. Post-action tree and screenshot.
14. Targeted keyboard text with readback.
15. Coordinate button click with readback.
16. Scroll delivery.
17. Window move and resize.
18. Drag delivery.

Raw logs, screenshots, user names, network addresses, and credentials are excluded from this repository.

## Public setup verification

The public installer has separate tests for configuration preservation, existing-connector replacement, repeat installation, and rollback conflicts. The checked-in desktop suite is adapted from the original VM checks and can be rerun with `uv run --locked scripts/verify.py --desktop --enable-accessibility`.

GitHub's default workflow runs unit tests and checks patch application. The manually dispatched desktop job builds from source and uses Xvfb/Openbox. Treat the workflow's actual result as the status of that run; this document does not assert that every future CI build or desktop environment passes.

Before the initial repository publication, the public scripts were also tested with uv 0.13.4 and Python 3.12.15 on the destination Lubuntu VM. An isolated installation preserved an unrelated MCP entry, a repeat installation changed zero files, all 18 desktop checks passed, and rollback restored the original isolated config and removed the installed launcher. Nine unit tests passed on Linux and Windows. This test reused the original checksummed binary; the manual CI job separately exercises a fresh source build.

## Known limitations

- This setup targets X11 on Ubuntu/Lubuntu 22.04. Wayland and other distributions require separate validation.
- The generic X11 activity overlay is unavailable in the pinned upstream version.
- Some existing apps need restarting after accessibility is enabled. Electron apps may require `--force-renderer-accessibility`.
- Firefox direct accessibility text writes were unreliable in the original source-machine checks. Targeted keyboard input with readback worked. The GTK test does not establish compatibility with every browser or app.
- The desktop remains shared with the user. Full verification briefly changes focus and pointer position.
- The drag patch needs revalidation when upstream changes its input dispatch or cancellation behavior.
- A fresh Codex session is required after connector registration. The verifier tests the MCP server directly, not a live Codex conversation.

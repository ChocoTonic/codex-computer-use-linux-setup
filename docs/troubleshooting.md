# Troubleshooting

## GLIBC version error

Build from source on the target Ubuntu 22.04 machine. Copying a binary from a distribution with a later GLIBC version can fail before MCP startup. The installer runs the executable before changing Codex configuration to catch this error.

## Rust build fails

Check `rustc --version` and `cargo --version`. The original build used Rust 1.99.1. Use an appropriate toolchain for the pinned lockfile, available disk space, and at least enough memory for a single Rust compiler process. The installer uses one build job and disables link-time optimization.

The build checkout must contain either clean upstream source or exactly the checked-in patch. Use a fresh `--source-dir` to keep unrelated local edits intact.

## SSH works but the desktop is unavailable

Log in to the VM's graphical desktop as the same Linux user. Confirm the X11 socket exists and the display is correct:

```bash
ls /tmp/.X11-unix/
DISPLAY=:0 wmctrl -l
```

Set `DISPLAY` and `XAUTHORITY` explicitly if the desktop uses a different display or authorization file. Do not use `xhost +` or disable X11 authentication.

## Accessibility tree is empty

Run the verifier with `--enable-accessibility`. This changes the saved GNOME toolkit-accessibility setting and the runtime AT-SPI state for your user. Restart the target app if it was already running when accessibility was disabled.

If you intentionally want to disable accessibility later, first close automation sessions that depend on it, then run:

```bash
gsettings set org.gnome.desktop.interface toolkit-accessibility false
```

A later desktop login refreshes session services. Installation rollback does not revert accessibility settings changed separately during verification.

## Existing computer-use connector

Review the current entry in `config.toml`. The installer refuses to replace a different command unless you pass `--replace-mcp`. It backs up the previous config before changing the table. Credentials and other servers remain untouched.

If your MCP configuration uses inline maps or unusual table syntax, convert the computer-use entry to a separate `[mcp_servers.computer-use]` table first. The installer deliberately refuses forms it cannot update safely.

## Codex still exposes old tools

Start a fresh Codex session. Confirm the launcher path with `codex mcp list`. Existing sessions can retain earlier tool schemas.

## Rollback reports changed files

Compare the current file with the corresponding `.before` file in the installation state directory. Preserve your edits, then restore or merge the previous connector entry manually. Do not restore an entire old Codex config over unrelated later changes.

## Report a failure

Include OS version, desktop environment, X11/Wayland session type, Rust version, and a redacted error. Verification results are private because they can contain window titles and screen contents. Review files before sharing them.

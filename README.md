# Codex computer-use setup for Lubuntu 22.04

Set up a locally built Linux desktop connector for Codex on **Ubuntu/Lubuntu 22.04, x86-64, X11**. The setup pins [agent-sh/computer-use-linux](https://github.com/agent-sh/computer-use-linux) to **v0.7.27** and adds a small X11 drag patch.

The upstream project by **Avi Fenesh** provides the MCP server, accessibility trees, screenshots, window targeting, and input tools. This repository provides installation, Codex configuration, rollback, and verification around that project. It is an independent community setup, with no OpenAI affiliation. See [Attribution](NOTICE.md) for the exact source commit and license.

## Why this setup exists

A release binary tested on Ubuntu 22.04 required a later GLIBC version than the host's GLIBC 2.35. Building the pinned source on Ubuntu 22.04 resolved that mismatch. An X11 drag patch added paced XTEST movement and button-release cleanup when an attempted drag fails.

The resulting setup was transferred between two Lubuntu Hyper-V VMs and passed 18 desktop checks. The public scripts generalize that setup to use your home directory, user ID, and Codex configuration. See [Validation](docs/validation.md) for the tested scope and limitations.

## Requirements

Use an active X11 desktop session owned by the same Linux user who runs Codex. SSH can launch the installer and connector, but the desktop must be logged in. VM disks do not need to be mounted from Windows.

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) to manage this project's Python environment. `uv run --locked` uses the checked-in `uv.lock` and `.python-version` (Python 3.12). There are no third-party Python dependencies. The desktop fixture uses Ubuntu's `/usr/bin/python3` so it can access the GTK bindings installed by `apt`.

You also need a Rust toolchain capable of building the pinned upstream dependencies. The original build used Rust **1.99.1**. Install Rust through the [official rustup installer](https://rustup.rs/) if needed. The repository does not install Rust or download a prebuilt backend automatically.

On Ubuntu 22.04, install these packages:

```bash
sudo apt-get update
sudo apt-get install -y \
  build-essential pkg-config git python3 python3-gi gir1.2-gtk-3.0 \
  at-spi2-core libatk-adaptor xdotool wmctrl dbus-x11
```

Codex must already be installed and signed in. See the [official Codex configuration documentation](https://learn.chatgpt.com/docs/config-file/config-basic) for configuration precedence and locations.

## Install

1. Clone this repository on the Linux VM:

   ```bash
   git clone https://github.com/ChocoTonic/codex-computer-use-linux-setup.git
   cd codex-computer-use-linux-setup
   ```

2. Build the pinned source and register the connector:

   ```bash
   uv run --locked scripts/setup.py
   ```

   This builds only the main MCP binary, applies `patches/x11-drag.patch`, and runs the upstream MCP contract check. Building can take several minutes. The build uses one job and disables link-time optimization to reduce memory use.

3. Enable accessibility and verify the connector:

   ```bash
   uv run --locked scripts/verify.py --enable-accessibility
   ```

   The flag enables saved and runtime AT-SPI accessibility for your Linux user. Already-running apps may need restarting before they expose their accessibility trees.

4. Run the optional desktop checks:

   ```bash
   uv run --locked scripts/verify.py --desktop --enable-accessibility
   ```

   This opens a disposable GTK window, tests observation and input, closes the window, and attempts to restore the previous focus. It moves the pointer and changes focus during testing. Run it when you can briefly leave the desktop idle.

5. Confirm the connector registration:

   ```bash
   codex mcp list
   ```

   Start a fresh Codex session and ask it to list desktop windows. The connector appears as `computer-use`.

## What changes

The installer writes the following user-owned files:

| Location | Purpose |
| --- | --- |
| `~/.local/bin/computer-use-linux` | X11 launcher with desktop session defaults |
| `~/.local/share/codex-computer-use-linux/releases/` | Locally built, checksum-addressed backend |
| `~/.local/share/codex-computer-use-linux/source/` | Pinned upstream checkout with the drag patch |
| `$CODEX_HOME/config.toml` or `~/.codex/config.toml` | The `mcp_servers.computer-use` entry |
| `$CODEX_HOME/skills/computer-use-linux/SKILL.md` | Usage guidance for Codex |
| `~/.local/state/codex-computer-use-linux/` | Private backups, rollback manifests, and verification results |

The installer preserves unrelated Codex settings and does not copy credentials, session history, or permission settings. An existing connector with a different command requires `--replace-mcp`; review its configuration before using that flag.

The launcher selects X11 explicitly, defaults to `DISPLAY=:0`, and derives the user runtime directory from `id -u`. Set `DISPLAY` and `XAUTHORITY` yourself if your desktop uses different values. The generic X11 activity overlay is disabled because this pinned version has no generic X11 renderer.

## Reuse a trusted local build

To transfer a build between compatible Linux machines, copy only the executable and compute its SHA-256 checksum on the source machine:

```bash
sha256sum /path/to/computer-use-linux
```

Pass that checksum on the destination machine:

```bash
uv run --locked scripts/setup.py \
  --binary /path/to/computer-use-linux \
  --sha256 YOUR_SOURCE_SHA256
```

Replace `YOUR_SOURCE_SHA256` with the 64-character checksum. This verifies transfer integrity; it does not establish the trustworthiness or patch history of an arbitrary binary. Both machines need compatible CPU architectures, GLIBC, and runtime dependencies. Run desktop verification on the destination.

## Roll back

The installer prints a manifest path for every run. To restore the changed files from that installation, pass the printed path:

```bash
uv run --locked scripts/setup.py --rollback /path/from/install/manifest.json
```

Rollback checks every managed file before writing. If you changed a managed file after installation, rollback stops so your edits can be reconciled manually. It retains the build checkout and audit records. Accessibility changes made by verification are separate from installation rollback; see [Troubleshooting](docs/troubleshooting.md).

## Development

Run the configuration and rollback tests:

```bash
uv sync --locked
uv run --locked python -m unittest discover -s tests -v
```

Pushes and pull requests run unit tests and check that the patch applies to the pinned upstream commit. The manual **Checks** workflow also builds the backend and runs the desktop suite in Xvfb/Openbox on Ubuntu 22.04. That virtual desktop does not replace testing on a real LXQt desktop.

Read [Architecture](docs/architecture.md), [Troubleshooting](docs/troubleshooting.md), and [Contributing](CONTRIBUTING.md) for maintenance details.

### Why Python and uv

Shell is sufficient for running the build and copying an executable. Python adds TOML parsing, checksummed backups, rollback conflict detection, and a JSON-RPC client for MCP verification. These parts benefit from structured data handling and tests. uv manages the interpreter and project environment; the installed MCP backend is a Rust executable launched by a small POSIX shell script, so routine Codex computer use does not run uv or this Python project.

## License and credit

Setup code and documentation are MIT licensed. The drag patch modifies upstream MIT-licensed code; the original copyright notice is preserved in [LICENSES/computer-use-linux.MIT.txt](LICENSES/computer-use-linux.MIT.txt). The locally installed backend retains that notice. See [NOTICE.md](NOTICE.md) for attribution and supporting projects.

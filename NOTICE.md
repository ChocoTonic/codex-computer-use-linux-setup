# Attribution and provenance

## Original backend

The desktop connector is based on **[agent-sh/computer-use-linux](https://github.com/agent-sh/computer-use-linux)**, created by **Avi Fenesh** and its contributors. This is the original implementation, not merely an inspiration for a rewritten backend.

This setup pins the following upstream revision:

- Release: `v0.7.27`
- Commit: [`3bb80c77be8e5fee5f871c2443ffed2c5156b5d1`](https://github.com/agent-sh/computer-use-linux/commit/3bb80c77be8e5fee5f871c2443ffed2c5156b5d1)
- Original copyright: `Copyright (c) 2026 Avi Fenesh`
- License: MIT, preserved verbatim in [LICENSES/computer-use-linux.MIT.txt](LICENSES/computer-use-linux.MIT.txt)

The backend is fetched from upstream during a source build. This repository does not vendor the complete backend or publish a prebuilt binary.

## Local additions

ChocoTonic's setup packages a locally developed X11 drag patch, an Ubuntu 22.04 source-build procedure, a portable X11 launcher, Codex MCP configuration, guarded rollback, and desktop verification. The initial setup and migration were developed with assistance from OpenAI Codex.

`patches/x11-drag.patch` modifies upstream `src/server.rs`. It adds paced `xdotool` drag movement and a best-effort button release after an attempted drag returns an error. Input cancellation and serialization also depend on the pinned upstream implementation. The patch is distributed under the MIT license, with both this repository's license and the upstream notice retained.

The GTK fixture and verification scripts were extracted and adapted from the local compatibility checks used during the VM setup. They are not represented as upstream's test suite. The installer also invokes upstream's own `scripts/mcp_safety_check.py` when building from source.

## Supporting projects

The setup relies on these independently maintained components:

- [xdotool](https://github.com/jordansissel/xdotool) for X11/XTEST input.
- [wmctrl](https://www.freedesktop.org/wiki/Software/wmctrl/) for X11 window discovery and control.
- [AT-SPI](https://gitlab.gnome.org/GNOME/at-spi2-core) for accessibility trees and semantic actions.
- [GTK](https://www.gtk.org/) and PyGObject for the disposable verification window.
- [OpenAI Codex](https://github.com/openai/codex) as the MCP client.

Those projects retain their own licenses. System packages are installed through Ubuntu's package manager and are not redistributed here. This repository is not affiliated with or endorsed by OpenAI, agent-sh, Ubuntu, or the Hyper-V project.

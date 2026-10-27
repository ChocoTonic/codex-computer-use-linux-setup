---
name: computer-use-linux
description: Observe and control a Linux X11 desktop through the computer-use MCP server, using accessibility trees, screenshots, window targeting, and verified input.
---

# Linux computer use

This installation uses [agent-sh/computer-use-linux](https://github.com/agent-sh/computer-use-linux), pinned to v0.7.27 with the ChocoTonic X11 drag patch. Setup and attribution are in [codex-computer-use-linux-setup](https://github.com/ChocoTonic/codex-computer-use-linux-setup).

1. Start with `get_app_state`, scoped to the intended app, PID, or window. Use `include_screenshot: false` when the accessibility tree answers the question.
2. Verify the target with `list_windows` or `focused_window` before sending input.
3. Prefer semantic elements from the fresh tree. Use screenshot coordinates when accessibility is unavailable. Re-observe after clicking, typing, scrolling, or dragging.
4. Target `type_text` to an exact window. Use `set_value` only when the target supports it, and require `verified: true` for exact-content confirmation. If Firefox does not update after a direct accessibility write, re-observe and use targeted keyboard input.
5. If the tree is truncated, scope more narrowly, increase the node budget, or use `get_tree_page`. Do not treat a partial tree as proof that a control is absent.
6. Use `doctor` for diagnostics. `setup_accessibility` enables saved and runtime AT-SPI accessibility; existing applications may need restarting.

The desktop is shared with the user. Actions can affect their active applications. Confirm the intended window and avoid changing unrelated applications. The generic X11 activity overlay is disabled because this upstream version has no generic X11 renderer.

The launcher supplies the X11 display, user runtime directory, D-Bus address, and Xauthority defaults. It deliberately selects X11 even when launched from an SSH session whose session type is `tty`. Keep this setup on X11; use upstream configuration for Wayland.

Start a fresh Codex session after installing or changing the MCP entry. Updating an npm package does not update this pinned local build.

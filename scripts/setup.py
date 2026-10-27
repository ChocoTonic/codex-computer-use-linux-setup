#!/usr/bin/env python3
"""Build and register a pinned computer-use-linux backend for Codex."""

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import tomllib

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = "https://github.com/agent-sh/computer-use-linux.git"
COMMIT = "3bb80c77be8e5fee5f871c2443ffed2c5156b5d1"
VERSION = "0.7.27-x11-local"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def atomic_write(path, data, mode=0o600):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".cu-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as output:
            output.write(data)
        os.chmod(name, mode)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def config_with_entry(text, launcher, replace=False):
    """Change only the computer-use table; preserve unrelated TOML verbatim."""
    parsed_before = tomllib.loads(text)
    # Refuse dotted keys/inline maps we cannot safely update without a TOML editor.
    if re.search(r"(?m)^\s*(?:mcp_servers\s*=|mcp_servers\.)", text):
        raise ValueError("Inline/dotted MCP config detected. Use a separate [mcp_servers.computer-use] table.")
    section = re.compile(
        r'(?ms)^\[mcp_servers\.(?:computer-use|"computer-use"|\'computer-use\')\][^\n]*\n.*?(?=^\s*\[|\Z)'
    )
    matches = list(section.finditer(text))
    if len(matches) > 1:
        raise ValueError("Duplicate computer-use tables. Repair config.toml first.")
    entry = '[mcp_servers.computer-use]\ncommand = ' + json.dumps(str(launcher)) + '\nargs = ["mcp"]\n'
    if matches:
        old = matches[0].group()
        expected = re.search(r'(?m)^command\s*=\s*' + re.escape(json.dumps(str(launcher))) + r'\s*$', old)
        if not replace:
            if expected and re.search(r'(?m)^args\s*=\s*\["mcp"\]\s*$', old):
                return text
            raise ValueError("computer-use already exists. Review it, then pass --replace-mcp to replace this table.")
        result = text[:matches[0].start()] + entry + "\n" + text[matches[0].end():]
    # Quoted/noncanonical table syntax could otherwise create a duplicate.
    elif re.search(r"(?mi)^\s*\[.*mcp_servers.*computer-use", text):
        raise ValueError("Noncanonical computer-use table detected. Use [mcp_servers.computer-use].")
    else:
        result = text.rstrip() + "\n\n" + entry
    parsed_after = tomllib.loads(result)
    # Reject edits that would alter unrelated semantic values, including a
    # table-looking line inside a multiline string or a nested MCP table.
    for parsed in (parsed_before, parsed_after):
        servers = parsed.get('mcp_servers', {})
        if not isinstance(servers, dict):
            raise ValueError('mcp_servers must be a TOML table.')
        servers.pop('computer-use', None)
        if not servers:
            parsed.pop('mcp_servers', None)
    if parsed_before != parsed_after:
        raise ValueError('Update would change unrelated configuration; refusing.')
    return result


def launcher_text(binary):
    return '''#!/bin/sh
set -eu
export PATH="$HOME/.local/bin:${PATH:-/usr/local/bin:/usr/bin:/bin}"
export DISPLAY="${DISPLAY:-:0}"
export XAUTHORITY="${XAUTHORITY:-$HOME/.Xauthority}"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
export DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=$XDG_RUNTIME_DIR/bus}"
# SSH sets this to tty. This launcher deliberately targets the X11 desktop.
export XDG_SESSION_TYPE=x11
export XDG_CURRENT_DESKTOP="${XDG_CURRENT_DESKTOP:-LXQt}"
export COMPUTER_USE_LINUX_SCREENSHOT_BACKEND=x11
# This upstream version has no generic X11 activity overlay.
export COMPUTER_USE_LINUX_INDICATOR=0
exec BINARY "$@"
'''.replace("BINARY", shlex.quote(str(binary)))


def build(source):
    if not source.exists():
        subprocess.run(["git", "clone", "--no-checkout", UPSTREAM, str(source)], check=True)
    actual = subprocess.check_output(["git", "-C", str(source), "remote", "get-url", "origin"], text=True).strip()
    if actual != UPSTREAM:
        raise ValueError("Build directory has an unexpected Git origin: " + actual)
    dirty = subprocess.check_output(["git", "-C", str(source), "status", "--porcelain"], text=True)
    patch = ROOT / "patches/x11-drag.patch"
    if dirty:
        revision = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
        diff = subprocess.check_output(["git", "-C", str(source), "diff", "HEAD", "--"])
        # Reuse our exact patched checkout. Never reset a user's edits.
        if revision != COMMIT or diff != patch.read_bytes() or "??" in dirty:
            raise ValueError("Build checkout has unrelated edits. Use a fresh --source-dir.")
    else:
        subprocess.run(["git", "-C", str(source), "fetch", "origin", COMMIT], check=True)
        subprocess.run(["git", "-C", str(source), "checkout", "--detach", COMMIT], check=True)
        subprocess.run(["git", "-C", str(source), "apply", "--check", str(patch)], check=True)
        subprocess.run(["git", "-C", str(source), "apply", str(patch)], check=True)
    env = dict(os.environ, CARGO_PROFILE_RELEASE_LTO="false",
               CARGO_PROFILE_RELEASE_CODEGEN_UNITS="16", CARGO_PROFILE_RELEASE_OPT_LEVEL="2",
               CARGO_INCREMENTAL="0")
    subprocess.run(["cargo", "build", "--release", "--locked", "--jobs", "1", "--bin", "computer-use-linux"],
                   cwd=source, env=env, check=True)
    binary = source / "target/release/computer-use-linux"
    subprocess.run([sys.executable, "scripts/mcp_safety_check.py", "--binary", str(binary), "--repo", "."],
                   cwd=source, check=True)
    return binary


def install_files(files, state):
    """Back up every changed file and record checksums for guarded rollback."""
    state.mkdir(parents=True, exist_ok=True)
    os.chmod(state, 0o700)
    records = []
    for index, (path, content, mode) in enumerate(files):
        path = Path(path).absolute()
        if path.is_symlink():
            raise ValueError("Refusing to replace symlink: " + str(path))
        if path.exists() and not path.is_file():
            raise ValueError("Expected regular file: " + str(path))
        if path.exists() and path.read_bytes() == content:
            continue
        record = {"path": str(path), "installed_sha256": digest(content), "backup": None, "mode": mode}
        if path.exists():
            saved = state / (str(index) + ".before")
            shutil.copy2(path, saved)
            os.chmod(saved, 0o600)
            record.update(backup=str(saved), before_mode=path.stat().st_mode & 0o777)
        records.append(record)
    # Save the recovery plan before the first write.
    atomic_write(state / "manifest.json", json.dumps({"version": VERSION, "files": records}, indent=2).encode())
    by_path = {str(Path(p).absolute()): (data, mode) for p, data, mode in files}
    for record in records:
        data, mode = by_path[record["path"]]
        atomic_write(record["path"], data, mode)
    return len(records)


def rollback(manifest):
    plan = json.loads(manifest.read_text())
    # Preflight every file before restoring any file.
    for item in plan["files"]:
        path = Path(item["path"])
        if path.is_symlink() or (path.exists() and digest(path.read_bytes()) != item["installed_sha256"]):
            raise ValueError("File changed since installation; refusing rollback: " + str(path))
        if item["backup"] and not Path(item["backup"]).is_file():
            raise ValueError("Missing backup: " + item["backup"])
    for item in reversed(plan["files"]):
        path = Path(item["path"])
        if item["backup"]:
            atomic_write(path, Path(item["backup"]).read_bytes(), item["before_mode"])
        elif path.exists():
            path.unlink()
    print("Restored previous files. Build checkout and audit records were retained.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, help="Use a previously built binary instead of building")
    parser.add_argument("--sha256", help="Required checksum for --binary")
    parser.add_argument("--source-dir", type=Path, default=Path.home()/".local/share/codex-computer-use-linux/source")
    parser.add_argument("--bin-dir", type=Path, default=Path.home()/".local/bin")
    parser.add_argument("--data-dir", type=Path, default=Path.home()/".local/share/codex-computer-use-linux")
    parser.add_argument("--state-dir", type=Path, default=Path.home()/".local/state/codex-computer-use-linux")
    parser.add_argument("--codex-home", type=Path, default=Path(os.environ.get("CODEX_HOME", Path.home()/".codex")))
    parser.add_argument("--replace-mcp", action="store_true", help="Replace an existing computer-use table after backup")
    parser.add_argument("--rollback", type=Path, metavar="MANIFEST")
    args = parser.parse_args()
    if args.rollback:
        rollback(args.rollback)
        return
    if sys.platform != "linux":
        parser.error("Run installation inside the Linux desktop VM.")
    for name in ('source_dir', 'bin_dir', 'data_dir', 'state_dir', 'codex_home'):
        setattr(args, name, getattr(args, name).expanduser().absolute())
    for command in ("xdotool", "wmctrl", "dbus-send", "gsettings"):
        if not shutil.which(command):
            parser.error("Missing " + command + ". Install the documented system packages first.")
    config = args.codex_home.expanduser().absolute()/"config.toml"
    launcher = args.bin_dir.expanduser().absolute()/"computer-use-linux"
    before = config.read_text() if config.exists() else ""
    after = config_with_entry(before, launcher, args.replace_mcp)
    if args.binary:
        if not args.sha256 or not re.fullmatch(r"[0-9a-fA-F]{64}", args.sha256):
            parser.error("--binary requires --sha256 with 64 hexadecimal characters.")
        binary = args.binary.expanduser().resolve()
        if digest(binary.read_bytes()) != args.sha256.lower():
            parser.error("Binary checksum mismatch.")
    else:
        for command in ("git", "cargo", "cc"):
            if not shutil.which(command):
                parser.error("Missing build prerequisite: " + command)
        binary = build(args.source_dir.expanduser().absolute())
    # Startup catches incompatible GLIBC before changing configuration.
    subprocess.run([str(binary), "--help"], stdout=subprocess.DEVNULL, check=True)
    destination = args.data_dir.expanduser().absolute()/"releases"/VERSION/digest(binary.read_bytes())[:16]/"computer-use-linux"
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    state = args.state_dir.expanduser().absolute()/stamp
    files = [(destination, binary.read_bytes(), 0o755),
             (launcher, launcher_text(destination).encode(), 0o755),
             (args.codex_home/"skills/computer-use-linux/SKILL.md", (ROOT/"skills/computer-use-linux/SKILL.md").read_bytes(), 0o644),
             (args.data_dir/"LICENSE.upstream", (ROOT/"LICENSES/computer-use-linux.MIT.txt").read_bytes(), 0o644),
             (config, after.encode(), 0o600)]
    count = install_files(files, state)
    print("Installed", VERSION, "with", count, "changed files.")
    print("Backup manifest:", state/"manifest.json")
    print("Run: uv run --locked scripts/verify.py --launcher", shlex.quote(str(launcher)), "--enable-accessibility")
    print("Then start a fresh Codex session to load the MCP tools.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        sys.exit(str(error))
